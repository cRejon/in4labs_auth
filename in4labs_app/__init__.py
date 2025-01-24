import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import Flask, session, request, redirect, render_template, url_for, flash, jsonify
from flask_login import LoginManager, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache

import docker
import bcrypt

from argon2 import PasswordHasher

from ..config import Config


# Export DOCKER_HOST environment variable to run in rootless mode
os.environ['DOCKER_HOST'] = 'unix:///run/user/1000/docker.sock'

db = SQLAlchemy()
login = LoginManager()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)
basedir = os.path.abspath(os.path.dirname(__file__))

# Add blueprint for auth
from . import auth
app.register_blueprint(auth.bp, url_prefix='/auth')

cache = Cache(app)

# Init sqlalchemy
db.init_app(app)

# Create db if not exists
from .models import Booking
from .auth.models import User
if not os.path.exists(os.path.join(basedir, 'in4labs.db')): 
    print('Creating database...')
    with app.app_context():
        db.create_all() # create tables in db

# Init login
login.init_app(app)
login.login_view='auth.login'

# Import labs config from Config object
lab_duration = Config.labs_config['duration']
labs = Config.labs_config['labs']

# Copy html files with lab instructions to templates folder
for lab in labs:
    lab_name = lab['lab_name']
    html_path = os.path.join(basedir, 'labs', lab_name, 'instructions.html')
    if os.path.exists(html_path):
        html_dest = os.path.join(basedir, 'templates', f'{lab_name}_instructions.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        with open(html_dest, 'w') as f:
            f.write(html_content)


# Create a hashed password for the Jupyter notebook
def create_hash(password):
    ph = PasswordHasher(memory_cost=10240, time_cost=10, parallelism=8)
    hash = ph.hash(password)
    hash = ':'.join(('argon2', hash))
    return hash

def setup_node_red(client, volume_name, nodered_dir, user_email):
    # Clean the volume for the new user
    volume = client.volumes.get(volume_name)
    volume.remove()
    client.volumes.create(volume_name)
    # Set the username and password for the node-red container
    # Generate bcrypt hash from the user email
    hashed_password = bcrypt.hashpw(user_email.encode(), bcrypt.gensalt()).decode()
    # Copy the default settings file
    settings_default_file = os.path.join(nodered_dir, 'settings_default.js')
    with open(settings_default_file, 'r') as file:
        js_content = file.read()
    # Use regular expressions to find and replace the username and password
    username_pattern = r'username:\s*"[^"]*"'
    password_pattern = r'password:\s*"[^"]*"'
    new_username_line = f'username: "{user_email}"'
    new_password_line = f'password: "{hashed_password}"'
    js_content = re.sub(username_pattern, new_username_line, js_content)
    js_content = re.sub(password_pattern, new_password_line, js_content)
    # Write the modified content in a settings.js file
    settings_file = os.path.join(nodered_dir, 'settings.js')
    with open(settings_file, 'w') as file:
        file.write(js_content)

def get_lab(lab_name):
    for lab in labs:
        if lab['lab_name'] == lab_name:
            return lab   
    flash(f'Lab not found.', 'error')
    return redirect(url_for('index'))
    

@app.route('/')
@login_required
def index():
    if len(labs) == 1:
        return redirect(url_for('book_lab', lab_name=labs[0]['lab_name']))
    else:
        return render_template('select_lab.html', labs=labs)

# Check a timeslot availability with AJAX
@app.route('/check_slot')
@login_required
def check_slot():
    lab_name = request.args.get('lab_name') # not used because actual labs are exclusive
    user_datetime = datetime.fromisoformat(request.args.get('user_datetime'))
    formatted_user_datetime = user_datetime.strftime('%d/%m/%Y @ %H:%Mh')
    utc_user_datetime = user_datetime.astimezone(timezone.utc)

    # Check if date_time is outdate
    actual_minute = datetime.now(timezone.utc).minute
    round_minute = actual_minute - (actual_minute % lab_duration)
    round_date_time = datetime.now(timezone.utc).replace(minute=round_minute, second=0, microsecond=0)
    if utc_user_datetime < round_date_time:
        response = f'''The date and time you selected ({formatted_user_datetime}) 
                       is outdate, please select a different one.'''
        return jsonify(response)

    booking = Booking.query.filter_by(date_time=utc_user_datetime).first()
    #booking = Booking.query.filter_by(lab_name=lab_name, date_time=utc_user_datetime).first()
    if booking is not None: # time slot is already booked
        response = f'''Time slot for {formatted_user_datetime} is already 
                       reserved, please select a different one.'''
    else:
        response = f'''Time slot for {formatted_user_datetime} is available.
                        Do you want to reserve the Lab? '''
         
    return jsonify(response)

from .forms import BookingForm
@app.route('/book/<lab_name>/', methods=['GET', 'POST'])
@login_required
def book_lab(lab_name):
    lab = get_lab(lab_name)
    
    form = BookingForm(lab_duration)
    if form.validate_on_submit():
        user_datetime = datetime.fromisoformat(form.date_time.data)
        formatted_user_datetime = user_datetime.strftime('%d/%m/%Y @ %H:%Mh')
        utc_user_datetime = user_datetime.astimezone(timezone.utc)
        # For security reasons, check again if the time slot is still available
        booking = Booking.query.filter_by(lab_name=lab_name, date_time=utc_user_datetime).first()
        if booking is not None: 
            flash('Someone has booked the Lab before you, please select a different time slot.', 'error')
            return redirect(url_for('book_lab', lab_name=lab_name))
        
        booking = Booking(user_id=current_user.id, lab_name=lab_name, date_time=utc_user_datetime)
        db.session.add(booking)
        db.session.commit()
        flash(f'{lab["html_name"]} reserved successfully for {formatted_user_datetime}', 'success')
        return redirect(url_for('book_lab', lab_name=lab_name))

    tpl_kwargs = {
        'lab': lab,
        'lab_duration': lab_duration,
        'user_email': current_user.email,
        'form': form,
    }
    return render_template('book_lab.html', **tpl_kwargs)

@app.route('/enter/<lab_name>/', methods=['GET'])
@login_required
def enter_lab(lab_name):
    lab = get_lab(lab_name) 

    actual_minute = datetime.now(timezone.utc).minute
    start_minute = actual_minute - (actual_minute % lab_duration)
    start_datetime = datetime.now(timezone.utc).replace(minute=start_minute, second=0, microsecond=0)
    booking = Booking.query.filter_by(lab_name=lab_name, date_time=start_datetime).first()
    
    if booking and (booking.user_id == current_user.id):
        client = docker.from_env()
        lab_image_name = f'{lab_name.lower()}:latest'
        # Create a unique container name with the lab name and the start date time
        container_name = f'{lab_name.lower()}-{start_datetime.strftime("%Y%m%d%H%M")}'
        host_port = lab['host_port']
        nat_port = lab['nat_port']
        default_volume = {'/dev/bus/usb': {'bind': '/dev/bus/usb', 'mode': 'rw'}}
        lab_volumes = default_volume.update(lab.get('volumes', {}))

        hostname = request.headers.get('Host').split(':')[0]
        lab_url = f'http://{hostname}:{nat_port}'
        end_time = start_datetime + timedelta(minutes=lab_duration)
        
        # Check if the lab needs extra containers
        extra_containers = lab.get('extra_containers', [])
        # Check if node-red is in extra_containers and get the nat port
        for extra_container in extra_containers:
            if extra_container['name'] == 'node-red':
                nodered_nat_port = extra_container['nat_port']
                break
            else:
                nodered_nat_port = 1880

        # Check if the actual time slot container is already running (e.g. the user click twice on the Enter button).
        # If so, redirect to the container url. If not, start the container
        try:
            container = client.containers.get(container_name)
            return redirect(lab_url)
        except docker.errors.NotFound:
            pass 
        
        # NOTE: The thread created by the StopContainersTask class sometimes doesn't stop the lab container,
        # so check if there is any previous container running and stop it  
        try:
            containers = client.containers.list()
            for container in containers:
                if container.name.startswith(lab_name.lower()):
                    container.stop()
        except docker.errors.NotFound:
            pass

        user_email = current_user.email
        # Use the user email as password for the Jupyter notebook
        notebook_password = create_hash(user_email)
        docker_env = {
            'USER_EMAIL': user_email,
            'USER_ID': current_user.id,
            'END_TIME': end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'CAM_URL': lab.get('cam_url', ''),
            'NOTEBOOK_PASSWORD': notebook_password,
            'NODE_RED_URL': f'http://{hostname}:{nodered_nat_port}',
        }
        
        containers = []
        # Start the extra containers
        for extra_container in extra_containers:
            if extra_container['name'] == 'node-red':
                volume_name = extra_container['volumes'].keys()[0]
                nodered_dir = os.path.join(basedir, 'labs', lab_name, 'node-red')
                setup_node_red(client, volume_name, nodered_dir, current_user.email)

            container_extra = client.containers.run(
                            extra_container['image'], 
                            name=extra_container["name"],
                            detach=True,
                            remove=True,
                            ports=extra_container['ports'],
                            volumes=extra_container.get('volumes', {}),
                            network=extra_container.get('network', ''),
                            command=extra_container.get('command', ''))
            containers.append(container_extra)
        # Run the lab container
        container_lab = client.containers.run(
                        lab_image_name, 
                        name=container_name,
                        detach=True, 
                        remove=True,
                        privileged=True,
                        volumes=lab_volumes,
                        ports={'8000/tcp': ('0.0.0.0', host_port)}, 
                        environment=docker_env)
        containers.append(container_lab)

        stop_containers = StopContainersTask(lab_name, containers, end_time, current_user.email)
        stop_containers.start()
        
        return redirect(lab_url)

    else:
        flash('You don´t have a reservation for the actual time slot, please make a booking.', 'error')
        return redirect(url_for('book_lab', lab_name=lab_name))

 
class StopContainersTask(threading.Thread):
     def __init__(self, lab_name, containers, end_time, user_email):
         super(StopContainersTask, self).__init__()
         self.lab_name = lab_name
         self.containers = containers
         self.end_time = end_time
         self.user_email = user_email
 
     def run(self):
        remaining_secs = (self.end_time - datetime.now(timezone.utc)).total_seconds()
        # Minus 3 seconds to avoid conflicts with the next time slot container
        time.sleep(remaining_secs - 3)
        # Save the container lab logs to a file
        logs = self.containers[0].logs()
        logs = logs.decode('utf-8').split('Press CTRL+C to quit')[1]
        logs = 'USER: ' + self.user_email + logs
        with open(f'{lab_name}_logs_UTC.txt', 'a') as f:
            f.write(logs)
        # Stop the containers
        for container in self.containers:
            container.stop()
        print('Lab containers stopped.')

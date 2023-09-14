import os
import threading
import time
from datetime import datetime, timedelta

from flask import Flask, session, request, redirect, render_template, url_for, flash, jsonify
from flask_login import LoginManager, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache

import docker

from argon2 import PasswordHasher

from .config import Config


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

try:   # for development purposes without docker
    # Create docker image if not exists
    client = docker.from_env()
    for lab in labs:
        lab_name = lab['lab_name']
        image_name = f'{lab_name.lower()}:latest'
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            print(f'Creating Docker image {image_name}.')
            dockerfile_path = os.path.join(basedir, 'labs', lab_name)
            image, build_logs = client.images.build(
                path=dockerfile_path,
                tag=image_name,
                rm=True,
            )
            for log in build_logs: # Print the build logs for debugging purposes
                print(log.get('stream', '').strip())
except:
    pass

# Create a hashed password for the Jupyter notebook
def create_hash(password):
    ph = PasswordHasher(memory_cost=10240, time_cost=10, parallelism=8)
    hash = ph.hash(password)
    hash = ':'.join(('argon2', hash))
    return hash

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
        return redirect(url_for('book_lab', lab=labs[0]))
    else:
        return render_template('select_lab.html', labs=labs)

# check a timeslot availability with AJAX
@app.route('/check_slot')
@login_required
def check_slot():
    lab_name = request.args.get('lab_name') # not used because actual labs are exclusive
    date = request.args.get('date')
    hour = request.args.get('hour')
    date_time = datetime.strptime(date + ' ' + hour, '%Y-%m-%d %H:%M')
    str_date_time = date_time.strftime('%d/%m/%Y @ %H:%Mh')

    minute = datetime.now().minute
    round_minute = minute - (minute % lab_duration)
    round_date_time = datetime.now().replace(minute=round_minute, second=0, microsecond=0)

    # Check if date_time is outdate
    if date_time < round_date_time:
        response = f'''The date and time you selected ({str_date_time}) 
                       is outdate, please select a different one.'''
        return jsonify(response)

    booking = Booking.query.filter_by(date_time=date_time).first()
    #booking = Booking.query.filter_by(lab_name=lab_name, date_time=date_time).first()
    if booking is not None: # time slot is already booked
        response = f'''Time slot for {str_date_time} is already 
                       reserved, please select a different one.'''
    else:
        response = f'''Time slot for {str_date_time} is available.
                        Do you want to reserve the Lab? '''
         
    return jsonify(response)

from .forms import BookingForm
@app.route('/book/<lab_name>/', methods=['GET', 'POST'])
@login_required
def book_lab(lab_name):
    lab = get_lab(lab_name)
    
    form = BookingForm(lab_duration)
    if form.validate_on_submit():
        # For security reasons, check again if the time slot is still available
        date_time = datetime.combine(form.date.data, form.hour.data)
        booking = Booking.query.filter_by(lab_name=lab_name, date_time=date_time).first()
        if booking is not None: 
            flash('Someone has booked the Lab before you, please select a different time slot.', 'error')
            return redirect(url_for('book_lab', lab_name=lab_name))
        
        booking = Booking(user_id=current_user.id, lab_name=lab_name, date_time=date_time)
        db.session.add(booking)
        db.session.commit()
        flash(f'{lab["html_name"]} reserved successfully for {date_time.strftime("%d/%m/%Y @ %H:%Mh.")}', 'success')
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

    minute = datetime.now().minute
    round_minute = minute - (minute % lab_duration)
    round_date_time = datetime.now().replace(minute=round_minute, second=0, microsecond=0)
    booking = Booking.query.filter_by(lab_name=lab_name, date_time=round_date_time).first()
    if booking and (booking.user_id == current_user.id):
        end_time = round_date_time + timedelta(minutes=lab_duration)
        # Use the user email as password for the Jupyter notebook
        notebook_password = create_hash(current_user.email)
        docker_env = {
            'USER_EMAIL': current_user.email,
            'USER_ID': current_user.id,
            'END_TIME': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'CAM_URL': lab.get('cam_url', ''),
            'NOTEBOOK_PASSWORD': notebook_password,
        }
        port = lab['host_port']
        container = client.containers.run(f'{lab_name}:latest', detach=True, remove=True,
                                            ports={'8000/tcp': ('0.0.0.0', port)}, environment=docker_env)

        remaining_secs = (end_time - datetime.now()).total_seconds()
        stop_container = StopContainerTask(container, remaining_secs)
        stop_container.start()
        
        hostname = request.headers.get('Host').split(':')[0]
        container_url = f'http://{hostname}:{port}'
        return redirect(container_url)
    
    flash('You don´t have a reservation for the actual time slot, please make a booking.', 'error')
    return redirect(url_for('book_lab', lab_name=lab_name))

 
class StopContainerTask(threading.Thread):
     def __init__(self, container, remaining_secs):
         super(StopContainerTask, self).__init__()
         self.container = container
         self.remaining_secs = remaining_secs
 
     def run(self):
        # Minus 2 seconds for safety
        time.sleep(self.remaining_secs - 2)
        self.container.stop()
        print('Container stopped.')

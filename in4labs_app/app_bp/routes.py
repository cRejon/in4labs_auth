import os
import time
import requests
from datetime import datetime, timedelta, timezone

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required

import docker

from in4labs_app import db, server_name, labs, lab_duration
from in4labs_app.app_bp import bp
from .models import Booking
from .forms import BookingForm
from .utils import StopContainersTask, setup_node_red, get_lab, create_hash


@bp.route('/')
@login_required
def index():
    if len(labs) == 1:
        return redirect(url_for('app.book_lab', lab_name=labs[0]['lab_name']))
    else:
        return render_template('select_lab.html', labs=labs, user_email=current_user.email)

@bp.route('/book/<lab_name>/', methods=['GET', 'POST'])
@login_required
def book_lab(lab_name):
    lab = get_lab(labs, lab_name)
    
    form = BookingForm(lab_duration)
    if form.validate_on_submit():
        user_datetime = datetime.fromisoformat(form.date_time.data)
        formatted_user_datetime = user_datetime.strftime('%d/%m/%Y @ %H:%Mh')
        utc_user_datetime = user_datetime.astimezone(timezone.utc)
        # For security reasons, check again if the time slot is still available
        booking = Booking.query.filter_by(lab_name=lab_name, date_time=utc_user_datetime).first()
        if booking is not None: 
            flash('Someone has booked the Lab before you, please select a different time slot.', 'error')
            return redirect(url_for('app.book_lab', lab_name=lab_name))
        
        booking = Booking(user_id=current_user.id, lab_name=lab_name, date_time=utc_user_datetime)
        db.session.add(booking)
        db.session.commit()
        flash(f'{lab["html_name"]} reserved successfully for {formatted_user_datetime}', 'success')
        return redirect(url_for('app.book_lab', lab_name=lab_name))

    tpl_kwargs = {
        'lab': lab,
        'lab_duration': lab_duration,
        'user_email': current_user.email,
        'form': form,
    }
    return render_template('book_lab.html', **tpl_kwargs)

# Check a timeslot availability with AJAX
@bp.route('/book/<lab_name>/check_slot')
@login_required
def check_slot(lab_name):
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

@bp.route('/enter/<lab_name>/', methods=['GET'])
@login_required
def enter_lab(lab_name):
    lab = get_lab(labs, lab_name)

    actual_minute = datetime.now(timezone.utc).minute
    start_minute = actual_minute - (actual_minute % lab_duration)
    start_datetime = datetime.now(timezone.utc).replace(minute=start_minute, second=0, microsecond=0)
    booking = Booking.query.filter_by(lab_name=lab_name, date_time=start_datetime).first()
    
    if booking and (booking.user_id == current_user.id):
        lab_url = f'/{server_name}/{lab_name}/'
        client = docker.from_env()
        # Create a unique container name with the lab name and the start date time
        container_name = f'{lab_name.lower()}-{start_datetime.strftime("%Y%m%d%H%M")}'

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

        containers = []
        # Check if the lab needs extra containers and run them
        extra_containers = lab.get('extra_containers', [])
        for extra_container in extra_containers:
            if extra_container['name'] == 'node-red':
                volume_name = list(extra_container['volumes'].keys())[0]
                basedir = os.path.abspath(os.path.dirname(__file__))
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
        lab_image_name = f'{lab_name.lower()}:latest'
        host_port = lab['host_port']
        lab_volumes = {'/dev/bus/usb': {'bind': '/dev/bus/usb', 'mode': 'rw'}}
        lab_volumes.update(lab.get('volumes', {}))
        end_time = start_datetime + timedelta(minutes=lab_duration)
        # Use the user email as password for the Jupyter notebook
        notebook_password = create_hash(current_user.email)
        docker_env = {
            'SERVER_NAME': server_name,
            'LAB_NAME': lab_name,
            'USER_EMAIL': current_user.email,
            'END_TIME': end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'CAM_URL': lab.get('cam_url', ''),
            'NOTEBOOK_PASSWORD': notebook_password,
        }

        container_lab = client.containers.run(
                        lab_image_name, 
                        name=container_name,
                        detach=True, 
                        remove=True,
                        privileged=True,
                        devices=['/dev/ttyACM[0-9]*:/dev/ttyACM[0-9]*:rwm'],
                        volumes=lab_volumes,
                        ports={'8000/tcp': ('0.0.0.0', host_port)}, 
                        environment=docker_env)
        containers.append(container_lab)

        stop_containers = StopContainersTask(lab_name, containers, end_time, current_user.email)
        stop_containers.start()

        # wait up to 10s for the container’s web server to respond
        start_time = time.time()
        timeout = 10
        while time.time() - start_time < timeout:
            try:
                r = requests.get(f'http://127.0.0.1:{host_port}', timeout=1)
                if 200 <= r.status_code < 500:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.5)

        return redirect(lab_url)

    else:
        flash('You don´t have a reservation for the actual time slot, please make a booking.', 'error')
        return redirect(url_for('.book_lab', lab_name=lab_name))

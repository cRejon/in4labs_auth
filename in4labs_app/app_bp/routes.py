import os
import time
import requests
from datetime import datetime, timedelta, timezone

from flask import current_app, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required

import docker

from in4labs_app import db, server_name, mountings, labs
from in4labs_app.app_bp import bp
from .models import Booking
from .forms import BookingForm
from .utils import StopContainersTask, setup_node_red, get_lab


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
    # get mounting & duration
    mounting = next((m for m in mountings if m['id'] == lab['mounting_id']), None)
    if mounting is None:
        flash('Invalid lab configuration.', 'error')
        return redirect(url_for('app.index'))
    lab_duration = mounting['duration']

    form = BookingForm(lab_duration)
    if form.validate_on_submit():
        user_datetime = datetime.fromisoformat(form.date_time.data)
        formatted_user_datetime = user_datetime.strftime('%d/%m/%Y @ %H:%Mh')
        utc_user_datetime = user_datetime.astimezone(timezone.utc)
        # check slot again
        booking = Booking.query.filter_by(
            mounting_id=lab['mounting_id'],
            date_time=utc_user_datetime
        ).first()
        if booking:
            flash('Someone else just booked that slot, please select a different one.', 'error')
            return redirect(url_for('app.book_lab', lab_name=lab_name))

        booking = Booking(
            user_id=current_user.id,
            mounting_id=lab['mounting_id'],
            lab_name=lab['lab_name'],
            date_time=utc_user_datetime
        )
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
    lab = get_lab(labs, lab_name)
    mounting = next((m for m in mountings if m['id'] == lab['mounting_id']), None)
    if mounting is None:
        return jsonify('Invalid lab configuration.')
    lab_duration = mounting['duration']
    mounting_id = lab['mounting_id']

    user_datetime = datetime.fromisoformat(request.args.get('user_datetime'))
    formatted_user_datetime = user_datetime.strftime('%d/%m/%Y @ %H:%Mh')
    utc_user_datetime = user_datetime.astimezone(timezone.utc)

    # no past slots
    actual = datetime.now(timezone.utc)
    round_minute = actual.minute - (actual.minute % lab_duration)
    round_dt = actual.replace(minute=round_minute, second=0, microsecond=0)
    if utc_user_datetime < round_dt:
        return jsonify(
            f'The date/time ({formatted_user_datetime}) is outdate, please select a different one.'
        )

    booking = Booking.query.filter_by(
        mounting_id=mounting_id,
        date_time=utc_user_datetime
    ).first()
    if booking:
        resp = f'''Time slot for {formatted_user_datetime} is already 
                       reserved, please select a different one.'''
    else:
        resp = f'''Time slot for {formatted_user_datetime} is available.
                        Do you want to reserve the Lab? '''
         
    return jsonify(resp)

@bp.route('/enter/<lab_name>/', methods=['GET'])
@login_required
def enter_lab(lab_name):
    lab = get_lab(labs, lab_name)
    mounting = next((m for m in mountings if m['id'] == lab['mounting_id']), None)
    if mounting is None:
        flash('Invalid lab configuration.', 'error')
        return redirect(url_for('app.index'))
    lab_duration = mounting['duration']

    now = datetime.now(timezone.utc)
    start_minute = now.minute - (now.minute % lab_duration)
    start_dt = now.replace(minute=start_minute, second=0, microsecond=0)

    booking = Booking.query.filter_by(
        mounting_id=lab['mounting_id'],
        lab_name=lab['lab_name'],
        date_time=start_dt
    ).first()
    if not booking or booking.user_id != current_user.id:
        flash("You don't have a reservation in this Lab for the current time slot.", 'error')
        return redirect(url_for('app.book_lab', lab_name=lab_name))

    lab_url = f'/{server_name}/{lab_name}/'
    host_port = mounting['host_port']
    if current_app.config['ENV'] != 'production': # don't use reverse proxy
        hostname = request.headers.get('Host').split(':')[0]
        lab_url = f'http://{hostname}:{host_port}/{server_name}/{lab_name}/'
    
    client = docker.from_env()
    # Create a unique container name with the lab name and the start date time
    container_name = f'{lab_name.lower()}-{start_dt.strftime("%Y%m%d%H%M")}'

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
    lab_volumes = {'/dev/bus/usb': {'bind': '/dev/bus/usb', 'mode': 'rw'}}
    lab_volumes.update(lab.get('volumes', {}))
    end_time = start_dt + timedelta(minutes=lab_duration)
    docker_env = {
        'SERVER_NAME': server_name,
        'LAB_NAME': lab_name,
        'USER_EMAIL': current_user.email,
        'END_TIME': end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'CAM_URL': mounting['cam_url'],
    }

    container_lab = client.containers.run(
                    lab_image_name, 
                    name=container_name,
                    detach=True, 
                    remove=True,
                    privileged=True,
                    #devices=['/dev/ttyACM[0-9]*:/dev/ttyACM[0-9]*:rwm'],
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

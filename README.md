DIEEC In4Labs base tool with _authorization_ support (no Moddle required)
=====
# Description
It brings together the common functionalities for all Labs: _login, time slot reservation_ and _access control_. The specific functionalities of each Lab must be implemented inside a Docker container (created by a Dockerfile) that will be run by this tool.  
It is possible to run several Labs in the same machine and all of them must be included in the **_in4labs_app/labs_** folder. Two sample laboratories (one for Arduino and one for Jupyter Notebooks) are provided for testing purposes, so their associated folders <ins>should be removed</ins> in production.  
Tested on Raspberry Pi OS Lite Bullseye (64-bit).  
Requires Python >=3.9.

# Setup Raspberry Pi
For convenience, copy this project inside **_/home/pi_** folder.
## Labs configuration
For each of the Labs that will be used, copy its repository in the mentioned _labs_ folder mentioned above (do not forget to delete the examples).  
Then, edit the **_in4labs_app/config.py_** file to fill it with the desired configuration. The _duration_ is common for all Labs and the _lab_name_ must be equal to the name given to the Lab repository. In Arduino laboratories, it is necessary to include the _cam_url_ of the webcam installed in the Lab.
```
# Labs settings
labs_config = {
    'duration': 10, # minutes
    'labs': [{
        'lab_name' : 'lab_1',
        'html_name' : 'Laboratory 1',
        'description' : 'Example of a remote laboratory for Arduino.',
        'host_port' : 8001,
        'cam_url': 'http://62.204.201.51:8100/Mjpeg/1?authToken=2454ef16-84cf-4184-a748-8bddd993c078',
    }, {
        'lab_name' : 'lab_2',
        'html_name' : 'Laboratory 2',
        'description' : 'Example of a remote laboratory for Jupyter Notebook.',
        'host_port' : 8002,
    }],
}
```
## Tool dependencies
Install Python libraries inside a virtual enviroment.
```
$ cd in4labs_auth
$ python -m venv venv
$ . venv/bin/activate
(venv) $ pip install -r requirements.txt
(venv) $ deactivate
```
## Docker
Install from bash script.
```
$ sudo apt update
$ curl -fsSL https://get.docker.com -o get-docker.sh
$ sudo sh get-docker.sh
$ rm get-docker.sh
```
Run the Docker daemon as a non-root user ([Rootless mode](https://docs.docker.com/engine/security/rootless/)).
```
$ sudo apt-get install -y uidmap fuse-overlayfs
$ sudo systemctl disable --now docker.service docker.socket
$ /usr/bin/dockerd-rootless-setuptool.sh install
$ export PATH=/usr/bin:$PATH
$ export DOCKER_HOST=unix:///run/user/1000/docker.sock
```
To launch the daemon on system startup, enable the systemd service and lingering:
```
$ systemctl --user enable docker
$ sudo loginctl enable-linger $(whoami)
```
## Running Gunicorn server on boot
1. Create a systemd service file:
```
$ sudo nano /etc/systemd/system/gunicorn.service
```
2. Add the following content to the file:
```
[Unit]
Description=In4Labs App
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/in4lab_auth
ExecStart=/home/pi/in4lab_auth/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:8000 -m 007 in4labs_app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
3. Reload systemd daemon:
```
$ sudo systemctl daemon-reload
```
4. Start and enable the service:
```
$ sudo systemctl start gunicorn
$ sudo systemctl enable gunicorn
```
5. Check the status of the service:
```
$ sudo systemctl status gunicorn
```

DIEEC In4Labs base tool with _authorization_ support (no Moddle required)
=====
# Description
This tool is the base for the In4Labs project.
It brings together the common functionalities for all Labs: _login, time slot reservation_ and _access control_. The specific functionalities of each Lab must be implemented inside a Docker image (created by a Dockerfile) that will be run by this tool. To access the tool, open a web browser and go to **_http://RPi_IP_address:8000_**.  
It is possible to run several Labs in the same machine and all of them must be included in the **_in4labs_app/labs_** folder. Two sample laboratories (one for Arduino and one for Jupyter Notebooks) are provided for testing purposes, so their associated folders <ins>should be removed</ins> in production.  
Tested on Raspberry Pi OS Lite Bullseye (64-bit).  
Requires Python >=3.9.

# Setup Raspberry Pi
The best way to burn the Raspberry Pi OS image is using [Raspberry Pi Imager](https://www.raspberrypi.org/software/). In advanced options, select _Enable SSH_, set _Username_ to **pi** and _Time zone_ to your local time zone.  
For convenience, copy this project inside **_/home/pi_** folder.
## Labs configuration
For each of the Labs that will be used, copy its repository in the _labs_ folder mentioned above (do not forget to delete the examples) and follow the installation instructions provided in its README file.  
Then, edit the **_in4labs_app/config.py_** file to fill it with the desired configuration. The `duration` is common for all Labs and the `lab_name` must be equal to the name given to the Lab repository. The URL of the webcam must be provided by the user and the NAT port must match the one given by the Internet router.
```
# Labs settings
labs_config = {
    'duration': 10, # minutes
    'labs': [{
        'lab_name' : 'lab_1',
        'html_name' : 'Laboratory 1',
        'description' : 'Example of a remote laboratory for Arduino.',
        'host_port' : 8001,
        'nat_port' : 8001,
        'cam_url': 'http://ULR_TO_WEBCAM/Mjpeg',
    }, {
        'lab_name' : 'lab_2',
        'html_name' : 'Laboratory 2',
        'description' : 'Example of a remote laboratory for Jupyter Notebook.',
        'host_port' : 8002,
        'nat_port' : 8002,
    }],
}
```
## Docker installation
1. Install Docker through its bash script selecting the version to **25.0.5**:
```
$ sudo apt update
$ curl -fsSL https://get.docker.com -o get-docker.sh
$ sudo sh get-docker.sh --version 25.0.5
```
2. Manage Docker as a non-root user:
``` 
$ sudo groupadd docker
$ sudo usermod -aG docker $USER
$ newgrp docker
```
## Tool dependencies
Install Python libraries inside a virtual enviroment.
```
$ cd $HOME/in4labs_auth
$ sudo apt install -y python3-venv && python3 -m venv venv
$ . venv/bin/activate
(venv) $ pip install -r requirements.txt
```
## Create Docker images
Docker images must be built before the first time the tool is run. The production server (Gunicorn) does not manage this process correctly, so this functionality is included in the **_create_images.py_** script. In the project folder and inside the virtual environment, run:
```
(venv) $ python create_images.py
```
This process can take a long time, so be patient.
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
WorkingDirectory=/home/pi/in4labs_auth
ExecStart=/home/pi/in4labs_auth/venv/bin/gunicorn --workers 2 --timeout 1800 --bind 0.0.0.0:8000 -m 007 in4labs_app:app
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

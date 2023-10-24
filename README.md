DIEEC In4Labs base tool with _authorization_ support (no Moddle required)
=====
# Description
This tool is the base for the In4Labs project.
It brings together the common functionalities for all Labs: _login, time slot reservation_ and _access control_. The specific functionalities of each Lab must be implemented inside a Docker container (created by a Dockerfile) that will be run by this tool. To access the tool, open a web browser and go to **_http://RPi_IP_address:8000_**.  
It is possible to run several Labs in the same machine and all of them must be included in the **_in4labs_app/labs_** folder. Two sample laboratories (one for Arduino and one for Jupyter Notebooks) are provided for testing purposes, so their associated folders <ins>should be removed</ins> in production.  
Tested on Raspberry Pi OS Lite Bullseye (64-bit).  
Requires Python >=3.9.

# Setup Raspberry Pi
The best way to burn the Raspberry Pi OS image is using [Raspberry Pi Imager](https://www.raspberrypi.org/software/). In advanced options, select _Enable SSH_, set _Username_ to **pi** and _Time zone_ to your local time zone.  
For convenience, copy this project inside **_/home/pi_** folder.
## Labs configuration
For each of the Labs that will be used, copy its repository in the _labs_ folder mentioned above (do not forget to delete the examples) and follow the installation instructions provided in its README file.  
Then, edit the **_in4labs_app/config.py_** file to fill it with the desired configuration. The `duration` is common for all Labs and the `lab_name` must be equal to the name given to the Lab repository. In Arduino laboratories, it is necessary to include the URL (`cam_url`) of the webcam installed in the Lab.
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
## Docker installation
1. Run the following command to uninstall all conflicting packages:
```
$ for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove $pkg; done
```
2. Add Docker's official GPG key:
```
$ sudo apt update
$ sudo apt install ca-certificates curl gnupg
$ sudo install -m 0755 -d /etc/apt/keyrings
$ curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
$ sudo chmod a+r /etc/apt/keyrings/docker.gpg
```
3. Add the repository to Apt sources:
```
$ echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
$ sudo apt update
```
4. Install the Docker packages:
```
$ sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
5. Manage Docker as a non-root user:
``` 
$ sudo groupadd docker
$ sudo usermod -aG docker $USER
$ newgrp docker
```
6. Verify that the installation is successful by running the _hello-world_ image:
```
$ docker run hello-world
```
## Tool dependencies
Install Python libraries inside a virtual enviroment.
```
$ cd in4labs_auth
$ sudo apt install -y python3-venv
$ python3 -m venv venv
$ . venv/bin/activate
(venv) $ pip install -r requirements.txt
```
## Create Docker images
Docker images must be built before the first time the tool is run. The production server (Gunicorn) does not manage this process correctly, so this functionality is included in the **_create_images.py_** script.  
In the project folder and inside the virtual environment, run:
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

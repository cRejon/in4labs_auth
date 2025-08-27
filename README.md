In4Labs base tool with _authorization_ support (no Moddle required) [![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]
=====
# Description
This tool is the base for the In4Labs project.
It brings together the common functionalities for all Labs: _login, time slot reservation_ and _access control_. The specific functionalities of each Lab must be implemented inside a Docker image (created by a Dockerfile) that will be run by this tool. Once it has been installed, open a web browser and go to **_http://<raspberry_IP_address>:8000_** to use the tool.  
Tested on Raspberry Pi OS Lite Bullseye (64-bit). Requires Python >=3.9.

# Setup Raspberry Pi
The best way to burn the Raspberry Pi OS image is using [Raspberry Pi Imager](https://www.raspberrypi.org/software/). In advanced options, select _Enable SSH_ and _Time zone_ to your local time zone.  
## Docker installation
1. Install Docker through its bash script selecting the version to **25.0.5**:
``` bash
sudo apt update
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh --version 25.0.5
```
2. Manage Docker as a non-root user:
```  bash
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
```
## Install this tool and its Python dependencies
Clone this project inside HOME directory and create a virtual environment to install the tool dependencies.
``` bash
sudo apt install -y git python3-venv
git clone https://github.com/cRejon/in4labs_auth.git $HOME/in4labs_auth
cd $HOME/in4labs_auth && python3 -m venv venv
. venv/bin/activate
(venv) pip install -r requirements.txt
```
## Labs installation
It is possible to run several Labs in the same machine and all of them must be included in the **_in4labs_app/labs_** folder. A sample laboratory named _example_lab_ is provided for testing purposes, so its associated folder <ins>should be removed</ins> in production. Clone the Labs you want to install and follow the instructions provided in their respective README files (Arduino board connections, extra configuration).  
For example, to use the _Internet of Things Lab_ and the _Cybersecurity Lab_ in the same physical mounting, run the following commands:
``` bash
cd $HOME/in4labs/in4labs_app/labs
rm -rf example_lab
git clone https://github.com/cRejon/in4labs_IoT.git
git clone https://github.com/cRejon/in4labs_cybersecurity.git
```
Then, edit the **_in4labs_app/config.py_** file and fill it with the correspondig configuration. The `duration` is common for Labs in the same mountig and the URL to the webcam's HLS stream (over HTTPS) must be provided by the user. This tool uses the port 8000 to serve the main app, so use the range 8001-8010 to set a unique `host_port` for each montage. The `lab_name` must be equal to the name given to the Lab repository and the `mounting_id` must match the one defined in the `mountings` section.  
``` python
labs_config = {
    'server_name': 'rasp1',
    'mountings': [{
        'id': '1', 
        'duration': 10, # minutes
        'cam_url': 'https://ULR_TO_WEBCAM/stream.m3u8',
        'host_port' : 8001,
    },],
    'labs': [{
        'lab_name' : 'in4labs_IoT',
        'html_name' : 'Laboratory of Internet of Things',
        'description' : 'This lab performs IoT experiments on Arduino devices',
        'mounting_id': '1',
    },{
        'lab_name' : 'in4labs_cybersecurity',
        'html_name' : 'Laboratory of Cybersecurity',
        'description' : 'This lab performs cybersecurity experiments on Arduino devices.',
        'mounting_id' : '1',
    }],
}
```
### Create Docker images
Docker images for Labs must be built before the first time the tool is run. The production server (Gunicorn) does not manage this process correctly, so this functionality is included in the **_create_images.py_** script. <u>Inside the virtual environment</u>, run:
``` bash
(venv) python $HOME/in4labs_auth/create_images.py
```
This process can take a long time, so be patient.
## Running Gunicorn server on boot
1. Create a systemd service file:
``` bash
sudo nano /etc/systemd/system/gunicorn.service
```
2. Add the following content to the file (replace `<your_username>` with your actual OS username):
```
[Unit]
Description=In4Labs App
After=network.target

[Service]
User=<your_username>
WorkingDirectory=/home/<your_username>/in4labs_auth
ExecStart=/home/<your_username>/in4labs_auth/venv/bin/gunicorn \
  --workers 2 \
  --timeout 1800 \
  --bind 0.0.0.0:8000 \
  -m 007 in4labs_app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
3. Reload systemd daemon:
``` bash
sudo systemctl daemon-reload
```
4. Start and enable the service:
``` bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```
5. Check the status of the service:
``` bash
sudo systemctl status gunicorn
```
# License
This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg

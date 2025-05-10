import os
import re
import threading
import time
from datetime import datetime, timezone

from flask import redirect, url_for, flash

import bcrypt

from argon2 import PasswordHasher


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
        logs = self.containers[-1].logs() # last container is the Lab container
        logs = logs.decode('utf-8').split('Press CTRL+C to quit')[1]
        logs = 'USER: ' + self.user_email + logs
        with open(f'{self.lab_name}_logs_UTC.txt', 'a') as f:
            f.write(logs)
        # Stop the containers
        for container in self.containers:
            container.stop()
        print('Lab containers stopped.')

def get_lab(labs, lab_name):
    for lab in labs:
        if lab['lab_name'] == lab_name:
            return lab   
    flash(f'Lab not found.', 'error')
    return redirect(url_for('app.index'))

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

# Create a hashed password for the Jupyter notebook
def create_hash(password):
    ph = PasswordHasher(memory_cost=10240, time_cost=10, parallelism=8)
    hash = ph.hash(password)
    hash = ':'.join(('argon2', hash))
    return hash
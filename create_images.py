import os

import docker

from in4labs_app.config import Config


basedir = os.path.abspath(os.path.dirname(__file__))
labs = Config.labs_config['labs']

# Create docker image for each lab if not exists
client = docker.from_env()
for lab in labs:
    lab_name = lab['lab_name']
    image_name = f'{lab_name.lower()}:latest'
    try:
        client.images.get(image_name)
        print(f'Docker image {image_name} already exists.')
    except docker.errors.ImageNotFound:
        print(f'Creating Docker image {image_name}. Be patient, this will take a while...')
        dockerfile_path = os.path.join(basedir, 'in4labs_app', 'labs', lab_name)
        image, build_logs = client.images.build(
            path=dockerfile_path,
            tag=image_name,
            rm=True,
        )
        for log in build_logs: # Print the build logs for debugging purposes
            print(log.get('stream', '').strip())
        print(f'Docker image {image_name} created successfully.')

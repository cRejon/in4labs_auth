import os

import docker

from config import Config


basedir = os.path.abspath(os.path.dirname(__file__))
# Export DOCKER_HOST environment variable to run in rootless mode
os.environ['DOCKER_HOST'] = 'unix:///run/user/1000/docker.sock'
client = docker.from_env()

# Function to create a Docker image from a Dockerfile
def create_docker_image(image_name, dockerfile_path):
    print(f'Creating Docker image {image_name}. Be patient, this will take a while...')
    image, build_logs = client.images.build(
        path=dockerfile_path,
        tag=image_name,
        rm=True,
    )
    for log in build_logs: # Print the build logs for debugging purposes
        print(log.get('stream', '').strip())
    print(f'Docker image {image_name} created successfully.')

# Create docker images if not exists
labs = Config.labs_config['labs']
for lab in labs:
    lab_name = lab['lab_name']
    lab_image_name = f'{lab_name.lower()}:latest'
    try:
        client.images.get(lab_image_name)
        print(f'Docker image {lab_image_name} already exists.')
    except docker.errors.ImageNotFound:
        lab_dockerfile_path = os.path.join(basedir, 'in4labs_app', 'labs', lab_name)
        create_docker_image(lab_image_name, lab_dockerfile_path)
    
    # Create or pull images in extra_containers
    extra_containers = lab.get('extra_containers', [])
    for container in extra_containers:
        image_name = container['image']
        try:
            client.images.get(image_name)
            print(f'Docker image {image_name} already exists.')
        except docker.errors.ImageNotFound:
            if container['name'] == 'node-red':
                # Create the node-red image
                nodered_dockerfile_path = os.path.join(basedir, 'in4labs_app', 'labs', lab_name, 'node-red')
                create_docker_image(image_name, nodered_dockerfile_path)
            else:
                print(f'Pulling Docker image {image_name}. Be patient, this will take a while...')
                client.images.pull(image_name)
                print(f'Docker image {image_name} pulled successfully.')
        
        # Create network 
        network_name = container['network']
        try:
            client.networks.get(network_name)
            print(f'Docker network {network_name} already exists.')
        except docker.errors.NotFound:
            print(f'Creating Docker network {network_name}.')
            client.networks.create(network_name)
            print(f'Docker network {network_name} created successfully.')

        # Create volumes
        volumes = container.get('volumes', {})
        for volume_name, volume in volumes.items():
            # Check if volume_name not starts with '/', so it is a volume and not a path
            if not volume_name.startswith('/'):
                try:
                    client.volumes.get(volume_name)
                    print(f'Docker volume {volume_name} already exists.')
                except docker.errors.NotFound:
                    print(f'Creating Docker volume {volume_name}.')
                    client.volumes.create(volume_name)
                    print(f'Docker volume {volume_name} created successfully.')

print('All Docker images and networks are ready.')

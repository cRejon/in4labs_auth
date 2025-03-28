import os
from tempfile import mkdtemp


basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    
    # Flask settings
    ENV = 'development'
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 600
    SECRET_KEY = 'replace-me',
    SESSION_TYPE= 'filesystem',
    SESSION_FILE_DIR = mkdtemp(),
    SESSION_COOKIE_NAME = 'in4labs-app-sessionid'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False   # should be True in case of HTTPS usage (production)
    SESSION_COOKIE_SAMESITE = None  # should be 'None' in case of HTTPS usage (production)
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    # database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'in4labs.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Labs settings
    labs_config = {
        'duration': 10, # minutes
        'labs': [{
            'lab_name' : 'lab_1',
            'html_name' : 'Laboratory 1',
            'description' : 'Example of a remote laboratory for Arduino.',
            'host_port' : 8001,
            'nat_port' : 8881,
            'cam_url': 'http://ULR_TO_WEBCAM/Mjpeg',
            'extra_containers': [{
                'name': 'mosquitto',
                'image': 'eclipse-mosquitto',
                'ports': {'1883/tcp': ('0.0.0.0', 1883)},
                'network': 'in4labs_net',
                'command': '',
            }]
        }, {
            'lab_name' : 'lab_2',
            'html_name' : 'Laboratory 2',
            'description' : 'Example of a remote laboratory for Jupyter Notebook.',
            'host_port' : 8002,
            'nat_port' : 8882,
        }],
    }


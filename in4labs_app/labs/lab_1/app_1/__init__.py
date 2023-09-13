import os
import sys
from datetime import datetime, timedelta

from flask import Flask, render_template


app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    
    tpl_kwargs = {
        'user_email': os.environ['USER_EMAIL'],
        'user_id': os.environ['USER_ID'],
        'end_time': os.environ['END_TIME'],
        'cam_url': os.environ['CAM_URL'],
    }
    return render_template('index.html', **tpl_kwargs)



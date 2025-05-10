from flask import Blueprint

bp = Blueprint('app', __name__,)

from . import routes
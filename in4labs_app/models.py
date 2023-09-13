from flask_login import UserMixin
from in4labs_app import login
from in4labs_app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False, unique=True)
    email = db.Column(db.String(64), nullable=False, unique=True)
    session_data = db.Column(db.Text)

    def __repr__(self):
        return f'<User {self.email}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False, unique=True)
    user_id = db.Column(db.Integer, nullable=False)
    lab_name = db.Column(db.String(64), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, unique=True)
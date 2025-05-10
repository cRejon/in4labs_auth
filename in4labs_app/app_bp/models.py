from in4labs_app import db


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False, unique=True)
    user_id = db.Column(db.Integer, nullable=False)
    lab_name = db.Column(db.String(64), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, unique=True)
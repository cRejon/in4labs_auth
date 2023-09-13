from datetime import datetime, time

from flask_wtf import FlaskForm
from wtforms import TimeField, SubmitField, DateField
from wtforms.validators import DataRequired


class BookingForm(FlaskForm):

    def __init__(self, lab_duration, *args, **kwargs):
        super(BookingForm, self).__init__(*args, **kwargs)
        self.lab_duration = lab_duration

    date = DateField('Date', 
                    #format='%Y-%m-%d', 
                    #default=datetime.now(),
                    validators=[DataRequired()])
    hour = TimeField('Hour', 
                    #format='%H:%M', 
                    #default= time(hour=datetime.now().hour, 
                    #             minute=datetime.now().minute),
                    validators=[DataRequired()])
    submit = SubmitField()

    def validate_hour(self, hour):
        round_minute = hour.data.minute - (hour.data.minute % self.lab_duration)
        self.hour.data = self.hour.data.replace(minute=round_minute)
        
        



    
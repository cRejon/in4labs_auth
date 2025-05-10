from flask_wtf import FlaskForm
from wtforms import TimeField, SubmitField, DateField, HiddenField
from wtforms.validators import DataRequired


class BookingForm(FlaskForm):

    def __init__(self, lab_duration, *args, **kwargs):
        super(BookingForm, self).__init__(*args, **kwargs)
        self.lab_duration = lab_duration

    date = DateField('Date', validators=[DataRequired()])
    time = TimeField('Time', validators=[DataRequired()])
    date_time = HiddenField(validators=[DataRequired()])
    submit = SubmitField()

    def validate_time(self, time):
        round_minute = time.data.minute - (time.data.minute % self.lab_duration)
        self.time.data = self.time.data.replace(minute=round_minute)
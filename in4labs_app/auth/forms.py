from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from .models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None or not user.check_password(self.password.data):
            raise ValidationError('Invalid e-mail address or password.')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Password', 
                                validators=[DataRequired(), EqualTo('password', message='Not matching.')])
    submit=SubmitField('Register')

    def validate_email(self, email):
        if len(email.data.split('@')) != 2:
            raise ValidationError('Wrong e-mail.')

        user=User.query.filter_by(email=email.data).first()
        if user is not None: # email exists
            raise ValidationError('This e-mail address is already registered.')
    
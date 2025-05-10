from flask import render_template, redirect, url_for
from .forms import LoginForm, RegistrationForm
from flask_login import current_user, login_user, logout_user
from .models import User
from in4labs_app import db

from in4labs_app.auth import bp


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('app.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        login_user(user)
        return redirect(url_for('app.index'))
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('app.index'))

@bp.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('app.index'))
    form =RegistrationForm()
    if form.validate_on_submit():
        user=User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)

    
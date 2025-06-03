import json

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import desc

from app import db
from app.controllers.device_controller import set_security
from app.forms import RegistrationForm, LoginForm
from app.models.user import User
from app.models.command import Command
from app.models.controller import Controller
from app.models.sensor_data import SensorData
from app.utils.dashboard_data import get_sensor_data
from app.utils.serial_reader import send_to_port

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()  # Створення форми

    if form.validate_on_submit():
        # Логіка реєстрації
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='user'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Реєстрація успішна! Тепер ви можете увійти', 'success')
        return redirect(url_for('user.login'))

    return render_template('user/user_register.html', form=form)  # Передаємо форму у шаблон

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # Створення форми

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('user.dashboard'))

        flash('Невірний логін або пароль', 'danger')

    return render_template('user/user_login.html', form=form)  # Передаємо форму у шаблон

@user_bp.route('/set_security_mode', methods=['POST'])
@login_required
def set_security_mode():
    data = request.get_json()
    mode = data.get('mode')

    try:
        set_security(mode)
        return jsonify({'status': 'success'})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': 'Server error: ' + str(e)}), 500

@user_bp.route('/dashboard')
@login_required
def dashboard():
    rooms_data=get_sensor_data(db)

    return render_template(
        'user/user_main.html', rooms_data=rooms_data)

@user_bp.route('/dashboard/data')
@login_required
def dashboard_data():

    rooms_data = get_sensor_data(db)
    return jsonify(rooms_data)

@user_bp.route('/devices')
@login_required
def device_management():

    return render_template('user/user_device_management.html')

@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('user.login'))
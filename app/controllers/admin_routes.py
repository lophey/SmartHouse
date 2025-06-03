from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.controllers.device_controller import set_security
from app.forms import AdminLoginForm
from app.models.command import Command
from app.models.sensor_data import SensorData
from app.models.user import User
from app.models.controller import Controller
from app.models.device import Device
from app.utils.dashboard_data import get_sensor_data
from app.utils.serial_reader import start_serial_readers

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = AdminLoginForm()  # Створення форми

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data) and user.is_admin():
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('admin.dashboard'))

        flash('Невірні облікові дані або недостатньо прав', 'danger')

    return render_template('admin/admin_login.html', form=form)  # Передаємо форму у шаблон

@admin_bp.route('/set_security_mode', methods=['POST'])
@login_required
def set_security_mode():
    if not current_user.is_admin():
        return jsonify({'error': 'Доступ заборонено'}), 403

    data = request.get_json()
    mode = data.get('mode')

    try:
        set_security(mode)
        return jsonify({'status': 'success'})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': 'Server error: ' + str(e)}), 500

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin():
        flash('Доступ заборонено', 'danger')
        return redirect(url_for('user.dashboard'))

    rooms_data=get_sensor_data(db)
    return render_template('admin/admin_main.html', rooms_data=rooms_data)

@admin_bp.route('/dashboard/data')
@login_required
def dashboard_data():
    if not current_user.is_admin():
        return jsonify({'error': 'Access denied'}), 403

    rooms_data = get_sensor_data(db)
    return jsonify(rooms_data)

@admin_bp.route('/devices')
@login_required
def device_management():

    return render_template('admin/admin_device_management.html')

@admin_bp.route('/manage_controllers')
@login_required
def manage_controllers():
    if not current_user.is_admin():
        flash('Доступ заборонено', 'danger')
        return redirect(url_for('user.dashboard'))
    controllers = Controller.query.all()

    return render_template('admin/manage_controllers.html', controllers=controllers)

@admin_bp.route('/add_controller', methods=['GET', 'POST'])
@login_required
def add_controller():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        device_id = request.form['device_id']
        has_buzzer = request.form['has_buzzer']
        if has_buzzer == 'True':
            has_buzzer = True
        else:
            has_buzzer = False
        description = request.form['description']
        port = request.form['port']

        new_controller = Controller(
            name=name,
            device_id=device_id,
            has_buzzer=has_buzzer,
            description=description,
            controller_port='COM'+port
        )
        db.session.add(new_controller)
        db.session.commit()

        flash('Controller added successfully', 'success')
        return redirect(url_for('admin.manage_controllers'))

    return render_template('admin/manage_controllers.html')

@admin_bp.route('/add_device', methods=['POST'])
@login_required
def add_device():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))

    controller_id = request.form['controller_id']
    name = request.form['name']
    name_arduino = request.form['name_arduino']
    device_type = request.form['type']
    location = request.form['device_location']

    new_device = Device(
        controllers_id=controller_id,
        name=name,
        name_arduino=name_arduino,
        type=device_type,
        location=location
    )
    db.session.add(new_device)
    db.session.commit()

    flash('Device added successfully', 'success')
    return redirect(url_for('admin.manage_controllers'))

@admin_bp.route('/delete_controller/<int:controller_id>', methods=['POST'])
@login_required
def delete_controller(controller_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))

    controller = Controller.query.get(controller_id)
    if controller:
        db.session.delete(controller)
        db.session.commit()
        flash('Controller deleted successfully', 'success')
    else:
        flash('Controller not found', 'danger')

    return redirect(url_for('admin.manage_controllers'))

@admin_bp.route('/delete_device', methods=['POST'])
@login_required
def delete_device():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    device_id = request.form.get('device_id')
    device = Device.query.get(device_id)
    if device:
        db.session.delete(device)
        db.session.commit()
        flash('Device deleted successfully', 'success')
    else:
        flash('Device not found', 'danger')

    return redirect(url_for('admin.manage_controllers'))

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))
import json

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import desc

from app import db
from app.forms import RegistrationForm, LoginForm
from app.models.user import User
from app.models.command import Command
from app.models.room import Room
from app.models.sensor_data import SensorData
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

@user_bp.route('/dashboard')
@login_required
def dashboard():
    rooms = Room.query.all()
    room_data = []

    for room in rooms:
        latest_data = SensorData.query.filter_by(room_id=room.room_id) \
            .order_by(SensorData.timestamp.desc()).first()

        if not latest_data:
            continue

        if room.name == 'ROOM2_ROOM3':
            # Room2 and Room3
            room_data.append({
                'room_id': f"{room.room_id}_1",
                'base_room_id': room.room_id,  # Реальный room_id
                'name': 'Room2',
                'device_id': room.device_id,
                'last_data': {
                    'temp': latest_data.raw.get('temp2'),
                    'hum': latest_data.raw.get('hum2'),
                    'ldr': latest_data.raw.get('ldr2'),
                    'gas': latest_data.raw.get('gas2'),
                    'fire': latest_data.raw.get('fire2'),
                    'motion': latest_data.raw.get('motion2'),
                    'dist': latest_data.raw.get('dist')
                },
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

            room_data.append({
                'room_id': f"{room.room_id}_2",
                'base_room_id': room.room_id,
                'name': 'Room3',
                'device_id': room.device_id,
                'last_data': {
                    'temp': latest_data.raw.get('temp3'),
                    'hum': latest_data.raw.get('hum3'),
                    'ldr': latest_data.raw.get('ldr3'),
                    'gas': latest_data.raw.get('gas3'),
                    'fire': latest_data.raw.get('fire3'),
                    'motion': latest_data.raw.get('motion3'),
                    'dist': latest_data.raw.get('dist')
                },
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

        elif room.name == 'BATHROOM_HALLWAY':
            # Bathroom and Hallway
            room_data.append({
                'room_id': f"{room.room_id}_1",
                'base_room_id': room.room_id,
                'name': 'Bathroom',
                'device_id': room.device_id,
                'last_data': {
                    'temp': latest_data.raw.get('tempBathroom'),
                    'hum': latest_data.raw.get('humBathroom'),
                    'ldr': latest_data.raw.get('ldrBathroom'),
                    'gas': latest_data.raw.get('gasBathroom'),
                    'fire': latest_data.raw.get('fireBathroom'),
                    'motion': latest_data.raw.get('motionBathroom')
                },
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

            room_data.append({
                'room_id': f"{room.room_id}_2",
                'base_room_id': room.room_id,
                'name': 'Hallway',
                'device_id': room.device_id,
                'last_data': {
                    'temp': latest_data.raw.get('tempHallway'),
                    'hum': latest_data.raw.get('humHallway'),
                    'ldr': latest_data.raw.get('ldrHallway'),
                    'gas': latest_data.raw.get('gasHallway'),
                    'fire': latest_data.raw.get('fireHallway'),
                    'motion': latest_data.raw.get('motionHallway')
                },
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

        else:
            # Обычная обработка для одиночных комнат
            room_data.append({
                'room_id': room.room_id,
                'name': room.name,
                'last_data': latest_data.raw if latest_data else {},
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

    security_cmd = Command.query.filter_by(
        command_type='SECURITY_MODE'
    ).order_by(Command.created_at.desc()).first()

    return render_template(
        'user/user_main.html',
        rooms=room_data,
        security_mode=security_cmd.command_value if security_cmd else 'OFF'
    )

def get_latest_command(room_id, command_type):
    cmd = Command.query.filter_by(
        room_id=room_id,
        command_type=command_type
    ).order_by(Command.created_at.desc()).first()
    return cmd.command_value if cmd else (26.0 if command_type == 'TRIGGER_TEMP' else 23.0)


@user_bp.route('/api/latest_data')
@login_required
def latest_data_api():
    rooms = Room.query.all()
    room_data = []

    for room in rooms:
        latest_data = SensorData.query.filter_by(room_id=room.room_id) \
            .order_by(SensorData.timestamp.desc()).first()

        if not latest_data:
            continue

        if room.name == 'ROOM2_ROOM3':
            # Room2 and Room3
            room_data.append({
                'room_id': f"{room.room_id}_1",
                'base_room_id': room.room_id,  # Реальный room_id
                'name': 'Room2',
                'device_id': room.device_id,
                'last_data': {
                    'temp': latest_data.raw.get('temp2'),
                    'hum': latest_data.raw.get('hum2'),
                    'ldr': latest_data.raw.get('ldr2'),
                    'gas': latest_data.raw.get('gas2'),
                    'fire': latest_data.raw.get('fire2'),
                    'motion': latest_data.raw.get('motion2'),
                    'dist': latest_data.raw.get('dist')
                },
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

            room_data.append({
                'room_id': f"{room.room_id}_2",
                'base_room_id': room.room_id,
                'name': 'Room3',
                'device_id': room.device_id,
                'last_data': {
                    'temp': latest_data.raw.get('temp3'),
                    'hum': latest_data.raw.get('hum3'),
                    'ldr': latest_data.raw.get('ldr3'),
                    'gas': latest_data.raw.get('gas3'),
                    'fire': latest_data.raw.get('fire3'),
                    'motion': latest_data.raw.get('motion3'),
                    'dist': latest_data.raw.get('dist')
                },
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

        elif room.name == 'BATHROOM_HALLWAY':
            # Bathroom and Hallway
            room_data.append({
                'room_id': f"{room.room_id}_1",
                'base_room_id': room.room_id,
                'name': 'Bathroom',
                'device_id': room.device_id,
                'last_data': {
                    'temp': latest_data.raw.get('tempBathroom'),
                    'hum': latest_data.raw.get('humBathroom'),
                    'ldr': latest_data.raw.get('ldrBathroom'),
                    'gas': latest_data.raw.get('gasBathroom'),
                    'fire': latest_data.raw.get('fireBathroom'),
                    'motion': latest_data.raw.get('motionBathroom')
                },
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

            room_data.append({
                'room_id': f"{room.room_id}_2",
                'base_room_id': room.room_id,
                'name': 'Hallway',
                'device_id': room.device_id,
                'last_data': {
                    'temp': latest_data.raw.get('tempHallway'),
                    'hum': latest_data.raw.get('humHallway'),
                    'ldr': latest_data.raw.get('ldrHallway'),
                    'gas': latest_data.raw.get('gasHallway'),
                    'fire': latest_data.raw.get('fireHallway'),
                    'motion': latest_data.raw.get('motionHallway')
                },
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

        else:
            # Single rooms
            room_data.append({
                'room_id': room.room_id,
                'base_room_id': room.room_id,
                'name': room.name,
                'device_id': room.device_id,
                'last_data': latest_data.raw if latest_data else {},
                'trigger_temp': get_latest_command(room.room_id, 'TRIGGER_TEMP'),
                'target_temp': get_latest_command(room.room_id, 'TARGET_TEMP')
            })

    security_cmd = Command.query.filter_by(
        command_type='SECURITY_MODE'
    ).order_by(Command.created_at.desc()).first()

    return jsonify({
        'rooms': room_data,
        'security_mode': security_cmd.command_value if security_cmd else 'OFF'
    })

@user_bp.route('/api/send_command', methods=['POST'])
@login_required
def send_command():
    data = request.get_json()
    room_id = data.get('room_id')
    command = data.get('command')

    if not room_id or not command:
        return jsonify({'error': 'Missing room_id or command'}), 400

    # Обрабатываем виртуальные room_id (например, room_id_1, room_id_2)
    base_room_id = room_id.split('_')[0] if '_' in room_id else room_id
    room = Room.query.get(int(base_room_id))
    if not room or not room.controller_port or not room.device_id:
        return jsonify({'error': 'Room, port, or device_id not found'}), 404

    # Сохраняем команду в базу
    command_type = command.split(':')[-2] if ':' in command else command
    command_value = command.split(':')[-1] if ':' in command else command
    cmd = Command(
        room_id=room_id,
        command_type=command_type,
        command_value=command_value,
        executed=False
    )
    db.session.add(cmd)
    db.session.commit()

    try:
        if send_to_port(room.controller_port, command):
            cmd.executed = True
            db.session.commit()
            return jsonify({'status': 'Command sent', 'command': command, 'port': room.controller_port}), 200
        else:
            db.session.rollback()
            return jsonify({'error': f'Failed to send command to {room.controller_port}'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error sending command: {str(e)}'}), 500

@user_bp.route('/api/set_global_mode', methods=['POST'])
@login_required
def set_global_mode():
    data = request.get_json()
    mode = data.get('mode')

    if not mode or mode not in ['OFF', 'HOME', 'AWAY']:
        return jsonify({'error': 'Invalid or missing mode'}), 400

    rooms = Room.query.filter(Room.controller_port.isnot(None), Room.device_id.isnot(None)).all()
    errors = []
    for room in rooms:
        command = f"{room.device_id}:SET_MODE:{mode}"
        cmd = Command(
            room_id=room.room_id,
            command_type='SET_MODE',
            command_value=mode,
            executed=False
        )
        db.session.add(cmd)
        try:
            if send_to_port(room.controller_port, command):
                cmd.executed = True
            else:
                errors.append(f"Failed to send to {room.controller_port}")
        except Exception as e:
            errors.append(f"Error for {room.controller_port}: {str(e)}")

    try:
        db.session.commit()
        if errors:
            return jsonify({'status': 'Partial success', 'errors': errors}), 207
        return jsonify({'status': 'Global mode set', 'mode': mode}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('user.login'))
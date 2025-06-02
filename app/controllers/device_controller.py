from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.room import Room
from app.models.command import Command
import serial
import threading

device_bp = Blueprint('device', __name__)

def send_command(port, command):
    try:
        with serial.Serial(port, baudrate=9600, timeout=1) as ser:
            ser.write(f"{command}\n".encode())
            print(f"Command sent to {port}: {command}")
    except serial.SerialException as e:
        print(f"Error sending command: {e}")

@device_bp.route('/control_light', methods=['POST'])
@login_required
def control_light():
    room_id = request.json.get('room_id')
    action = request.json.get('action')  # 'ON' or 'OFF'

    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404

    command_str = f"{room.name}:LIGHT:{action}"
    cmd = Command(
        room_id=room_id,
        command_type='LIGHT',
        command_value=action
    )
    db.session.add(cmd)
    db.session.commit()

    # Отправка команды в отдельном потоке
    threading.Thread(
        target=send_command,
        args=(room.controller_port, command_str)
    ).start()

    return jsonify({'status': 'success', 'command': command_str})

@device_bp.route('/set_temp', methods=['POST'])
@login_required
def set_temp():
    room_id = request.json.get('room_id')
    temp_type = request.json.get('type')  # 'TRIGGER_TEMP' or 'TARGET_TEMP'
    value = request.json.get('value')

    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404

    command_str = f"{room.name}:{temp_type}:{value}"
    cmd = Command(
        room_id=room_id,
        command_type=temp_type,
        command_value=str(value)
    )
    db.session.add(cmd)
    db.session.commit()

    threading.Thread(
        target=send_command,
        args=(room.controller_port, command_str)
    ).start()

    return jsonify({'status': 'success', 'command': command_str})

@device_bp.route('/set_security_mode', methods=['POST'])
@login_required
def set_security_mode():
    mode = request.json.get('mode')  # 'OFF', 'HOME', 'AWAY'

    rooms = Room.query.all()
    for room in rooms:
        if room.controller_port:
            command_str = f"{room.name}:SET_MODE:{mode}"
            threading.Thread(
                target=send_command,
                args=(room.controller_port, command_str)
            ).start()

            cmd = Command(
                room_id=room.room_id,
                command_type='SECURITY_MODE',
                command_value=mode
            )
            db.session.add(cmd)

    db.session.commit()
    return jsonify({'status': 'success', 'mode': mode})
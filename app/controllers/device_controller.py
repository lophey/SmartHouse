from collections import defaultdict

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models.controller import Controller
from app.models.command import Command
import serial
import threading

from app.models.device import Device
from app.models.relay_actions import RelayAction
from app.models.sensor_data import SensorData

# Создадим Blueprint для админской части управления устройствами
admin_device_bp = Blueprint('admin_devices', __name__, url_prefix='/admin/devices')

# Создадим Blueprint для пользовательской части управления устройствами
user_device_bp = Blueprint('user_devices', __name__, url_prefix='/user/devices')

def set_security(mode):
    if mode not in ['OFF', 'HOME', 'AWAY']:
        raise ValueError("Невірний режим")

    controllers = Controller.query.all()

    for controller in controllers:
        new_command = Command(
            controllers_id=controller.controllers_id,
            command_type='SET_MODE',
            command_value=mode
        )
        db.session.add(new_command)

    db.session.commit()
    return True


# Админские эндпоинты
@admin_device_bp.route('/', methods=['GET'])
@login_required
def admin_devices_list():
    if not current_user.is_admin():
        return "Доступ заборонено", 403

    return render_devices_list(is_admin=True)

@admin_device_bp.route('/control', methods=['POST'])
@login_required
def admin_control_device():
    if not current_user.is_admin():
        return jsonify({'error': 'Доступ заборонено'}), 403

    return control_device()

@admin_device_bp.route('/set_temperature', methods=['POST'])
@login_required
def admin_set_temperature():
    if not current_user.is_admin():
        return jsonify({'error': 'Доступ заборонено'}), 403

    return set_temperature()

# Пользовательские эндпоинты
@user_device_bp.route('/', methods=['GET'])
@login_required
def user_devices_list():
    return render_devices_list(is_admin=False)

@user_device_bp.route('/control', methods=['POST'])
@login_required
def user_control_device():
    return control_device()

@user_device_bp.route('/set_temperature', methods=['POST'])
@login_required
def user_set_temperature():
    return set_temperature()


def render_devices_list(is_admin):
    # Получаем все устройства типа relay, кроме вытяжек
    relay_devices = Device.query.filter(
        Device.type == 'relay',
        Device.name_arduino.isnot(None),
        ~Device.name.contains('Витяжка')  # Исключаем вытяжки
    ).all()

    # Получаем последние состояния для каждого устройства
    subquery = db.session.query(
        RelayAction.device_id,
        func.max(RelayAction.timestamp).label('max_timestamp')
    ).group_by(RelayAction.device_id).subquery()

    last_states = db.session.query(RelayAction).join(
        subquery,
        (RelayAction.device_id == subquery.c.device_id) &
        (RelayAction.timestamp == subquery.c.max_timestamp)
    ).all()

    # Создаем словарь состояний устройств
    device_states = {state.device_id: state.state for state in last_states}

    # Получаем последние температурные настройки для каждого контроллера
    temp_types = [
        'targetTempRoom1', 'triggerTempRoom1',
        'targetTempHallway', 'triggerTempHallway',
        'targetTempRoom2', 'triggerTempRoom2',
        'targetTempRoom3', 'triggerTempRoom3'
    ]

    # Подзапрос для получения последних температур
    temp_subquery = db.session.query(
        SensorData.controllers_id,
        SensorData.type,
        func.max(SensorData.timestamp).label('max_ts')
    ).filter(SensorData.type.in_(temp_types)) \
    .group_by(SensorData.controllers_id, SensorData.type) \
    .subquery()

    temp_data = db.session.query(SensorData).join(
        temp_subquery,
        (SensorData.controllers_id == temp_subquery.c.controllers_id) &
        (SensorData.type == temp_subquery.c.type) &
        (SensorData.timestamp == temp_subquery.c.max_ts)
    ).all()

    # Создаем словарь температурных настроек
    controller_temps = defaultdict(dict)
    for data in temp_data:
        # Определяем тип температуры (target или trigger)
        temp_type = "target" if "target" in data.type.lower() else "trigger"
        controller_temps[data.controllers_id][temp_type] = data.value

    # Группируем устройства по комнатам (локациям)
    rooms = defaultdict(lambda: {
        'name': '',
        'lighting_devices': [],
        'ac_device': None,
        'controller_id': None,
        'target_temp': 23.0,  # Значение по умолчанию
        'trigger_temp': 26.0   # Значение по умолчанию
    })

    # Добавляем устройства в комнаты
    for device in relay_devices:
        room_name = device.location

        # Инициализируем комнату
        if not rooms[room_name]['name']:
            rooms[room_name]['name'] = room_name
            rooms[room_name]['controller_id'] = device.controllers_id

        # Добавляем состояние устройства
        device.state = device_states.get(device.device_id, False)

        # Определяем тип устройства
        if 'AC' in device.name_arduino:
            rooms[room_name]['ac_device'] = device
        else:
            rooms[room_name]['lighting_devices'].append(device)

    # Добавляем температурные настройки
    for room in rooms.values():
        controller_id = room['controller_id']
        if controller_id in controller_temps:
            if 'target' in controller_temps[controller_id]:
                room['target_temp'] = controller_temps[controller_id]['target']
            if 'trigger' in controller_temps[controller_id]:
                room['trigger_temp'] = controller_temps[controller_id]['trigger']

    # Преобразуем словарь в список для шаблона
    rooms_list = list(rooms.values())

    rooms_list.sort(key=lambda x: x['name'])

    template_name = 'admin/admin_device_management.html' if is_admin else 'user/user_device_management.html'
    return render_template(template_name, rooms=rooms_list)

def control_device():
    data = request.get_json()
    device_id = data.get('device_id')
    state = data.get('state')  # "ON" или "OFF"

    if not device_id or state not in ['ON', 'OFF']:
        return jsonify({'error': 'Не вірні параметри'}), 400

    device = Device.query.get(device_id)
    if not device:
        return jsonify({'error': 'Пристрій не знайдено'}), 404

    # Проверяем, что устройство имеет name_arduino
    if not device.name_arduino:
        return jsonify({'error': 'Пристрій не має команди для Arduino'}), 400

    controller = Controller.query.get(device.controllers_id)
    if not controller or not controller.controller_port:
        return jsonify({'error': 'Контролер не знайдено'}), 404

    # Формируем команду напрямую используя name_arduino
    command_value = f"{device.name_arduino}:{state}"
    command_type = "RELAY"

    # Создаем команду
    new_command = Command(
        controllers_id=controller.controllers_id,
        command_type=command_type,
        command_value=command_value
    )

    # Создаем запись в relay_actions
    new_action = RelayAction(
        device_id=device.device_id,
        state=(state == "ON"),
        triggered_by='user'
    )

    db.session.add(new_command)
    db.session.add(new_action)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': f"Команда {command_value} поставлена в чергу"
    })

def set_temperature():
    data = request.get_json()
    controller_id = data.get('controller_id')
    temp_type = data.get('type')  # 'target' или 'trigger'
    value = data.get('value')

    if not controller_id or temp_type not in ['target', 'trigger'] or not value:
        return jsonify({'error': 'Не вірні параметри'}), 400

    try:
        float_value = float(value)
    except ValueError:
        return jsonify({'error': 'Температура повинна бути числом'}), 400

    controller = Controller.query.get(controller_id)
    if not controller:
        return jsonify({'error': 'Контролер не знайдено'}), 404

    # Формируем команду для Arduino
    command_value = f"{temp_type.upper()}_TEMP:{float_value}"
    command_type = "TEMP"

    # Создаем команду для отправки
    new_command = Command(
        controllers_id=controller.controllers_id,
        command_type=command_type,
        command_value=command_value
    )

    # Создаем запись в sensor_data
    # Определяем тип в зависимости от комнаты
    room_name = "Room1" if "ROOM1" in controller.name else "Hallway"
    sensor_type = f"{temp_type}Temp{room_name}"

    new_sensor_data = SensorData(
        controllers_id=controller_id,
        type=sensor_type,
        value=float_value
    )

    db.session.add(new_command)
    db.session.add(new_sensor_data)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': f"Температура {temp_type} встановлена на {float_value}°C"
    })
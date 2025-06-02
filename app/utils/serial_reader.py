import serial
import json
import threading
from datetime import datetime
import time
from app import db
from app.models.room import Room
from app.models.events import Event
from app.models.sensor_data import SensorData



def read_from_port(app, port, room_id):
    with app.app_context():
        try:
            ser = serial.Serial(port, baudrate=9600, timeout=1)
            print(f"Listening on port {port} for room {room_id}")

            while True:
                try:
                    data = ser.readline().decode(errors='ignore').strip()
                    if data:
                        print(f"[{port}] RAW: {data}")
                        if data.startswith("ALARM:"):
                            alarm_type = data.split(':')[1]
                            save_alarm(room_id, alarm_type)
                            broadcast_alarm(room_id, alarm_type)  # Рассылка ALARM
                        elif data.startswith('{'):
                            json_data = json.loads(data)
                            save_sensor_data(room_id, json_data)
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    print(f"Error processing data on {port}: {e}")
        except serial.SerialException as e:
            print(f"Serial error on {port}: {e}")
            time.sleep(5)

def broadcast_alarm(source_room_id, alarm_type):
    try:
        # Находим комнаты с баззерами
        buzzer_rooms = Room.query.filter_by(has_buzzer=True).all()
        for room in buzzer_rooms:
            if room.room_id != source_room_id and room.controller_port and room.device_id:
                command = f"{room.device_id}:ALARM:{alarm_type}"
                send_to_port(room.controller_port, command)
                print(f"Broadcasted ALARM:{alarm_type} to {room.device_id} on {room.controller_port}")
    except Exception as e:
        print(f"Error broadcasting alarm: {e}")

PORT_MAPPING = {
    'COM1': 'COM5',  # KITCHEN
    'COM2': 'COM6',  # ROOM1
    'COM3': 'COM7',  # ROOM2_ROOM3
    'COM4': 'COM8'   # BATHROOM_HALLWAY
}

def send_to_port(port, command, retries=3):
    # Используем маппинг для преобразования порта базы данных в порт Proteus
    proteus_port = PORT_MAPPING.get(port, port)
    for attempt in range(retries):
        try:
            ser = serial.Serial(proteus_port, baudrate=9600, timeout=1)
            ser.write(f"{command}\n".encode())
            ser.flush()
            ser.close()
            return True
        except serial.SerialException as e:
            time.sleep(2)
    return False

def save_sensor_data(room_id, data):
    try:
        for key, val in data.items():
            if key == "device":
                continue
            sensor_data = SensorData(
                room_id=room_id,
                type=key,
                value=float(val),
                raw = data,
                timestamp=datetime.utcnow()
            )
            db.session.add(sensor_data)
        db.session.commit()
        print(f"Sensor data saved for room {room_id}: {data}")
    except Exception as e:
        print(f"Database error while saving sensor data: {e}")
        db.session.rollback()


def save_alarm(room_id, alarm_type):
    try:
        event = Event(
            room_id=room_id,
            type='alert',
            description=f"Alarm triggered: {alarm_type}",
            timestamp=datetime.utcnow()
        )
        db.session.add(event)
        db.session.commit()
        print(f"Alarm saved: {alarm_type} in room {room_id}")
    except Exception as e:
        print(f"Error saving alarm: {e}")
        db.session.rollback()


def start_serial_readers(app):
    with app.app_context():
        rooms = Room.query.all()
        for room in rooms:
            if room.controller_port:
                print(f"Starting reader for {room.name} on {room.controller_port}")
                thread = threading.Thread(
                    target=read_from_port,
                    args=(app, room.controller_port, room.room_id),
                    daemon=True
                )
                thread.start()
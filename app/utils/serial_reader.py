import serial
import json
import threading
from datetime import datetime
import time
from app import db
from app.models.controller import Controller
from app.models.device import Device
from app.models.events import Event
from app.models.sensor_data import SensorData

serial_handlers = {}
def read_from_port(app, port, controller_id):
    with app.app_context():
        try:

            if port in serial_handlers:
                ser = serial_handlers[port]
            else:
                ser = serial.Serial(port, baudrate=9600, timeout=1)
                serial_handlers[port] = ser
                print(f"Opened port {port} for controller {controller_id}")

            print(f"Listening on port {port} for room {controller_id}")

            while True:
                try:
                    data = ser.readline().decode(errors='ignore').strip()
                    if data:
                        print(f"[{port}] RAW: {data}")
                        if data.startswith("ALARM:"):
                            parts = data.split(':')
                            alarm_type = parts[1] if len(parts) > 1 else None
                            device_arduino_name = parts[2] if len(parts) > 2 else None

                            device_id = None
                            if device_arduino_name:
                                device = Device.query.filter_by(name_arduino=device_arduino_name).first()
                                if device:
                                    device_id = device.device_id

                            save_alarm(controller_id, alarm_type, device_id)
                            broadcast_alarm(controller_id, alarm_type, device_id)
                        elif data.startswith('{'):
                            json_data = json.loads(data)
                            save_sensor_data(controller_id, json_data)
                except Exception as e:
                    print(f"Read error on {port}: {e}")
                    time.sleep(1)
        except serial.SerialException as e:
            print(f"Serial error on {port}: {e}")
            time.sleep(5)

def broadcast_alarm(source_controller_id, alarm_type, device_id):
    try:
        device_name = None
        if device_id is not None:
            device = Device.query.get(device_id)
            if device:
                device_name = device.name_arduino

        buzzer_controllers = Controller.query.filter_by(has_buzzer=True).all()
        for controller in buzzer_controllers:
            if controller.controllers_id != source_controller_id and controller.controller_port and controller.device_id:
                if device_name:
                    command = f"{controller.device_id}:ALARM:{alarm_type}:{device_name}"
                else:
                    command = f"{controller.device_id}:ALARM:{alarm_type}"
                send_to_port(controller.controller_port, command)
                print(f"Broadcasted {command} to {controller.device_id} on {controller.controller_port}")
    except Exception as e:
        print(f"Error broadcasting alarm: {e}")

def send_to_port(port, command, retries=3):
    try:
        if port in serial_handlers:
            ser = serial_handlers[port]
            ser.write(f"{command}\n".encode())
            ser.flush()
            print(f"Sent via existing handler to {port}: {command}")
            return True
    except Exception as e:
        print(f"Error sending via handler to {port}: {e}")

    for attempt in range(retries):
        try:
            with serial.Serial(port, baudrate=9600, timeout=1) as ser:
                ser.write(f"{command}\n".encode())
                ser.flush()
                print(f"Sent via temporary connection to {port}: {command}")
                return True
        except serial.SerialException as e:
            print(f"Error sending to {port}: {e}")
            time.sleep(2)
    return False

def command_dispatcher(app, interval=5):
    with app.app_context():
        from app.models.command import Command
        from app.models.controller import Controller

        while True:
            try:
                pending_commands = Command.query.filter_by(executed=False).all()

                for cmd in pending_commands:
                    controller = Controller.query.get(cmd.controllers_id)

                    if controller and controller.controller_port:

                        if cmd.command_type == 'SET_MODE':
                            command_str = f"{controller.device_id}:SET_MODE:{cmd.command_value}"
                        elif cmd.command_type == 'RELAY':
                            command_str = f"{controller.device_id}:{cmd.command_value}"
                        elif cmd.command_type == 'TEMP':
                            command_str = f"{controller.device_id}:{cmd.command_value}"
                        else:
                            command_str = cmd.command_value

                        if send_to_port(controller.controller_port, command_str):
                            cmd.executed = True
                            print(f"Command executed: {command_str}")

                db.session.commit()
                time.sleep(interval)

            except Exception as e:
                print(f"Command dispatcher error: {e}")
                db.session.rollback()
                time.sleep(10)


def save_sensor_data(controller_id, data):
    try:
        for key, val in data.items():
            if key == "device":
                continue
            sensor_data = SensorData(
                controllers_id=controller_id,
                type=key,
                value=float(val),
                raw = data,
                timestamp=datetime.now()
            )
            db.session.add(sensor_data)
        db.session.commit()
        print(f"Sensor data saved for controller {controller_id}: {data}")
    except Exception as e:
        print(f"Database error while saving sensor data: {e}")
        db.session.rollback()


def save_alarm(controller_id, alarm_type, device_id=None):
    try:
        event = Event(
            controllers_id=controller_id,
            device_id=device_id,
            type='alert',
            description=f"Alarm triggered: {alarm_type}",
            timestamp=datetime.now()
        )
        db.session.add(event)
        db.session.commit()
        print(f"Alarm saved: {alarm_type} for controller {controller_id}, device {device_id}")
    except Exception as e:
        print(f"Error saving alarm: {e}")
        db.session.rollback()


def start_serial_readers(app):
    with app.app_context():
        controllers = Controller.query.all()
        for controller in controllers:
            if controller.controller_port:
                print(f"Starting reader for {controller.name} on {controller.controller_port}")
                thread = threading.Thread(
                    target=read_from_port,
                    args=(app, controller.controller_port, controller.controllers_id),
                    daemon=True
                )
                thread.start()
                command_thread = threading.Thread(
                    target=command_dispatcher,
                    args=(app,),
                    daemon=True
                )
                command_thread.start()
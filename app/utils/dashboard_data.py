from app.models.device import Device
from app.models.sensor_data import SensorData
from app import db

def get_sensor_data(db):
    # Отримуємо унікальні локації з активними датчиками
    locations = db.session.query(Device.location).filter(
        Device.type == 'sensor',
        Device.is_active == True
    ).distinct().all()

    rooms_data = []

    for loc in locations:
        location = loc[0]
        # Отримуємо всі датчики для локації
        sensors = Device.query.filter(
            Device.location == location,
            Device.type == 'sensor',
            Device.is_active == True
        ).order_by(Device.name).all()

        room_sensors = []
        for sensor in sensors:
            # Останні дані для датчика
            latest_data = SensorData.query.filter(
                SensorData.type == sensor.name_arduino
            ).order_by(SensorData.timestamp.desc()).first()

            if latest_data:
                # Визначаємо одиниці виміру
                unit = determine_unit(sensor.name_arduino)
                room_sensors.append({
                    'name': sensor.name,
                    'value': format_value(latest_data.value, sensor.name_arduino),
                    'unit': unit,
                    'timestamp': latest_data.timestamp.strftime('%H:%M:%S')
                })
            # Потім у циклі для кожної кімнати
            room_sensors.sort(key=lambda x: (get_sensor_category(x['name']), x['name']))

        rooms_data.append({
            'location': location,
            'sensors': room_sensors
        })

    # Сортування кімнат за назвою локації
    rooms_data.sort(key=lambda x: x['location'])

    return rooms_data

def determine_unit(sensor_type):
    if 'temp' in sensor_type:
        return '°C'
    elif 'hum' in sensor_type:
        return '%'
    elif 'dist' in sensor_type:
        return 'cm'
    return ''

def format_value(value, sensor_type):
    if 'fire' in sensor_type:
        return 'Пожежа' if value > 256 else 'Вогонь відсутній'
    elif 'gas' in sensor_type:
        return 'Високий рівень' if value > 300 else 'Нормальний вміст'
    elif 'motion' in sensor_type:
        return 'Помічено рух' if value > 0 else 'Рух відсутній'
    elif 'reed' in sensor_type:
        return 'Відкрито' if value == 1 else 'Закрито'
    elif 'water' in sensor_type:
        return 'Залиття' if value > 200 else 'Нормально'
    return round(value, 1)

def get_sensor_category(name):
    if 'температури' in name: return 1
    if 'вологості' in name: return 2
    if 'дим' in name or 'газу' in name: return 3
    if 'руху' in name: return 4
    if 'вогню' in name: return 5
    if 'освітленості' in name: return 6
    if 'води' in name: return 7
    if 'Магнітний' in name: return 8
    if 'відстані' in name: return 9
    return 10  # Інші типи
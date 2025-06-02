from app import db

class Room(db.Model):
    __tablename__ = 'rooms'
    room_id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50))
    has_buzzer = db.Column(db.Boolean)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    controller_port = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=db.func.now())

    devices = db.relationship("Device", backref="room", lazy=True)
    commands = db.relationship("Command", backref="room", lazy=True)
    sensor_data = db.relationship("SensorData", backref="room", lazy=True)

    def __repr__(self):
        return f'<Room {self.name}>'
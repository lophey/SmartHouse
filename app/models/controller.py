from app import db

class Controller(db.Model):
    __tablename__ = 'controllers'
    controllers_id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50))
    has_buzzer = db.Column(db.Boolean)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    controller_port = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=db.func.now())

    devices = db.relationship("Device", backref="controller", lazy=True)
    commands = db.relationship("Command", backref="controller", lazy=True)
    sensor_data = db.relationship("SensorData", backref="controller", lazy=True)

    def __repr__(self):
        return f'<Controller {self.name}>'
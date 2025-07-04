from app import db

class Device(db.Model):
    __tablename__ = 'devices'
    device_id = db.Column(db.Integer, primary_key=True)
    controllers_id = db.Column(db.Integer, db.ForeignKey('controllers.controllers_id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    name_arduino = db.Column(db.String(50))
    type = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    is_active = db.Column(db.Boolean, default=True)

    events = db.relationship("Event", backref="device", lazy=True)
    def __repr__(self):
        return f'<Device {self.name} ({self.type})>'
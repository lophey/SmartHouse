from app import db
from datetime import datetime

class RelayAction(db.Model):
    __tablename__ = 'relay_actions'

    action_id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.device_id', ondelete='CASCADE'), nullable=False)
    state = db.Column(db.Boolean, nullable=False)  # True = включено, False = выключено
    triggered_by = db.Column(
        db.String(20),
        nullable=False,
        server_default='user',
    )
    timestamp = db.Column(db.DateTime, default=datetime.now())

    # Связь с моделью Device (если нужно)
    device = db.relationship("Device", backref=db.backref("relay_actions", lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<RelayAction id={self.action_id}, device_id={self.device_id}, state={self.state}, triggered_by={self.triggered_by}>"
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

from app import db

class SensorData(db.Model):
    __tablename__ = 'sensor_data'
    data_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.room_id', ondelete='SET NULL'), index=True)
    type = db.Column(db.String(50), nullable=False)  # Додати
    value = db.Column(db.Float, nullable=False)
    raw = db.Column(JSONB)  # Додати
    timestamp = db.Column(db.DateTime, server_default=func.now(), index=True)

    def __repr__(self):
        return f'<SensorData {self.type} for room {self.room_id} at {self.timestamp}>'

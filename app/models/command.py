from app import db
from datetime import datetime

class Command(db.Model):
    __tablename__ = 'commands'
    command_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.room_id'))
    command_type = db.Column(db.String(20), nullable=False)
    command_value = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed = db.Column(db.Boolean, default=False)

    # command_room = db.relationship('Room', backref='room_commands')

    def __repr__(self):
        return f'<Command {self.command_type}={self.command_value} for room {self.room_id}>'
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.controller import Controller
from app.models.command import Command
import serial
import threading

device_bp = Blueprint('devices', __name__)

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


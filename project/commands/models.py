from project import db
from enum import Enum


class StatusMessageEnum(Enum):
    LOST = "LOST"
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"


class AirConCommand(db.Model):
    __tablename__ = "aircon_command"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.String(128), unique=True, nullable=False)
    temperature = db.Column(db.Integer, nullable=False)

    def __init__(self, uid, temperature, *args, **kwargs):
        self.uid = uid
        self.temperature = temperature


class TemperatureSensorMessage(db.Model):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid: str = db.Column(db.String(128), unique=True, nullable=False)
    temperature: int = db.Column(db.Integer, nullable=False)

    def __init__(self, uid, temperature, *args, **kwargs):
        self.uid = uid
        self.temperature = temperature


class StatusMessage(db.Model):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    status: str = db.Column(db.Enum(StatusMessageEnum), nullable=False, default=StatusMessageEnum.LOST)
    sensor_message_id = db.Column(db.Integer, db.ForeignKey('temperature_sensor_message.id'))
    sensor_message = db.relationship('TemperatureSensorMessage', backref='status_messages')
    aircon_command_id = db.Column(db.Integer, db.ForeignKey('aircon_command.id'))
    aircon_command = db.relationship('AirConCommand', backref='status_messages')

    def __init__(self, status, sensor_message_id, aircon_command_id, *args, **kwargs):
        self.status = status
        self.sensor_message_id = sensor_message_id
        self.aircon_command_id = aircon_command_id


class LastMessages(db.Model):
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ac_last_message: bool = db.Column(db.Boolean, default=False, nullable=True)
    t_sensor_last_message: bool = db.Column(db.Boolean, default=False, nullable=True)

    def __init__(self, ac_last_message, t_sensor_last_message, *args, **kwargs):
        self.ac_last_message = ac_last_message
        self.t_sensor_last_message = t_sensor_last_message

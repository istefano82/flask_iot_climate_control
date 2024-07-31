import asyncio

from werkzeug.exceptions import abort
from project import create_app, ext_celery
from flask import request, jsonify, current_app, Response, abort
from project.commands.models import *
from project.cache import cache

from project.commands.tasks import send_status, process_lost_commands



app = create_app()
celery = ext_celery.celery

@app.route("/")
def hello_world():
    return "Hello, World!"


@app.route("/api/v1/services/air-conditioner", methods=('POST',))
def create_air_conditioner_command():
    if request.method == 'POST':
        request_data = request.get_json()
        try:
            if request_data.get('last'):
                current_app.logger.info(f'Last command received {request_data["last"]}')
                last_sensor_message = cache.get("t_sensor_last_message")
                if last_sensor_message:
                    current_app.logger.debug(f'Last sensor message found {last_sensor_message}')
                    process_lost_commands.delay()
                    cache.delete("t_sensor_last_message")
                else:
                    current_app.logger.debug('No last sensor message found, saving last AC command')
                    cache.set("ac_last_message", True, timeout=1800)
                    current_app.logger.debug(f"Last AC command saved to cache {cache.get('ac_last_message')}")
                return Response("Last AC command received", 200)
        except KeyError as e:
            return abort(500, f"Last AC command received with error {e}")

        try:
            # Create an AirConditionerCommand model instance
            current_app.logger.info(f'Creating air conditioner command with params {request_data}')
            ac_command = AirConCommand(uid=request_data.get("uid"), temperature=request_data.get("temperature"))
            db.session.add(ac_command)
            db.session.commit()
            current_app.logger.info(f"Air conditioner command saved to database object is {ac_command}")
            # Check for a matching message
            matching_message = TemperatureSensorMessage.query.filter_by(uid=ac_command.uid).first()
            current_app.logger.info(f"Matching message is {matching_message}")
            if matching_message:
                # Create a StatusMessage model instance
                # Update the status message
                if matching_message.temperature == ac_command.temperature:
                    status_message = StatusMessage(aircon_command_id=ac_command.id, sensor_message_id=matching_message.id, status="MATCH")
                    current_app.logger.info("status_message.status is MATCH")
                else:
                    status_message = StatusMessage(aircon_command_id=ac_command.id, sensor_message_id=matching_message.id,
                                                   status="MISMATCH")
                    current_app.logger.info("status_message.status is MISMATCH")
                current_app.logger.info(f'Creating status message {status_message}')
                db.session.add(status_message)
                db.session.commit()
                current_app.logger.info(f"Status message saved to database object is {status_message}")
                # send_status.delay(ac_command.uid, status_message.status)

            return Response("Command received", 201)
        except Exception as e:
            current_app.logger.error(f"Error processing ac command: {e}")
            abort(500, f"Error processing ac command: {e}")

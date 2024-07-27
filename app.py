import asyncio

from werkzeug.exceptions import HTTPException

from project import create_app, ext_celery
from flask import request, jsonify, current_app
from project.commands.models import *

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
        if request_data['last'] == True:
            current_app.logger.info(f'Last command received {request_data["last"]}')
            last_sensor_message = LastMessages.objects.first_or_none(t_sensor_last_message=True)
            if last_sensor_message:
                current_app.logger.debug(f'Last sensor message found {last_sensor_message}')
                asyncio.create_task(process_lost_commands())
                last_sensor_message.delete()
            else:
                current_app.logger.debug('No last sensor message found, saving last AC command')
                LastMessages(ac_last_message=True).save()
            return jsonify({"message": "Last AC command received"}, status_code=200)

        try:
            # Create an AirConditionerCommand model instance
            current_app.logger.info(f'Creating air conditioner command with params {request_data}')
            ac_command = AirConCommand(uid=request_data["uid"], temperature=request_data["temperature"])

            # Save the command to the database
            db_ac_command = ac_command.save()
            current_app.logger.info(f"Air conditioner command saved to database object is {db_ac_command}")
            # Check for a matching message
            matching_message = TemperatureSensorMessage.objects.first_or_none(uid=db_ac_command.uid)
            current_app.logger.info(f"Matching message is {matching_message}")
            if matching_message:
                # Create a StatusMessage model instance
                status_message = StatusMessage(aircon_command=db_ac_command, sensor_message=matching_message)
                current_app.logger.info(f'Creating status message {status_message}')
                # Update the status message
                if matching_message.temperature == db_ac_command.temperature:
                    status_message.status = "MATCH"
                    current_app.logger.info("status_message.status is MATCH")
                else:
                    status_message.status = "MISMATCH"
                    current_app.logger.info("status_message.status is MISMATCH")
                result = status_message.save()
                current_app.logger.info(f"Status message saved to database object is {result}")
                send_status(db_ac_command.uid, status_message.status)

            return jsonify({"message": "Command received"}, status_code=200)
        except Exception as e:
            current_app.logger.error(f"Error processing ac command: {e}")
            raise HTTPException(status_code=500, detail=str(e))

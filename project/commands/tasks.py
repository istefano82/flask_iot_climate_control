from celery import shared_task
import logging
import requests
import os

from project import db
from project.commands.models import StatusMessage, AirConCommand

from flask import request, jsonify, current_app

# logger = logging.getLogger(__name__)




@shared_task
def divide(x, y):
    import time
    time.sleep(5)
    return x / y


@shared_task(ignore_result=True)
def send_status(uid, status):
    """Send a status message to the Status service."""
    from app import app
    with app.app_context():
        current_app.logger.info(f'Sending status message with uid {uid} and status {status}')
        data = {"uid": uid, "status": status}
        try:
            response = requests.post(os.getenv('STATUS_SERVICE_URL', 'http://localhost:8080/api/v1/status'), json=data)
            current_app.logger.info(f'Response is {response}')
            if response.status_code != 200:
                current_app.logger.error(f"Error sending status message: {response.text}")
        except Exception as e:
            current_app.logger.error(f"Error sending status message: {e}")


def find_lost_messages():
    """Finds all AirConditionerCommands that don't have a corresponding TemperatureSensorMessage."""
    # Get all AirConCommand IDs
    from app import app
    with app.app_context():
        ac_command_ids = [ac_command.id for ac_command in AirConCommand.query.all()]

        # Get all StatusMessage AirConCommand IDs
        status_message_ac_command_ids = [status_message.aircon_command_id for status_message in StatusMessage.query.all()]

        # Find the difference between the two lists
        lost_command_ids = set(ac_command_ids) - set(status_message_ac_command_ids)

        # Get the AirConCommand objects with the lost IDs
        lost_commands = AirConCommand.query.filter(AirConCommand.id.in_(lost_command_ids)).all()

        return lost_commands


@shared_task(ignore_result=True)
def process_lost_commands():
    """Processes lost commands in a non-blocking manner."""
    from app import app
    with app.app_context():
        import time
        time.sleep(5)
        app.logger.debug('SLeeping 10 seconds')
        lost_commands = find_lost_messages()

        for lost_command in lost_commands:
            result = StatusMessage(aircon_command_id=lost_command.id, sensor_message_id=None, status="LOST")
            db.session.add(result)
            db.session.commit()
            app.logger.debug(f'Created status message result {result} for {lost_command}')
            send_status(lost_command.uid, result.status)
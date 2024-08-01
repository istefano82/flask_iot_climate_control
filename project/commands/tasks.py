from celery import shared_task
import logging
import requests
import os

from project import db
from project.commands.models import StatusMessage

logger = logging.getLogger(__name__)



@shared_task
def divide(x, y):
    import time
    time.sleep(5)
    return x / y


@shared_task()
def send_status(uid, status):
    """Send a status message to the Status service."""
    logger.info(f'Sending status message with uid {uid} and status {status}')
    data = {"uid": uid, "status": status.value}
    try:
        response = requests.post(os.getenv('STATUS_SERVICE_URL', 'http://localhost:8080/api/v1/status'), json=data)
        logger.info(f'Response is {response}')
        if response.status_code != 200:
            logger.error(f"Error sending status message: {response.text}")
    except Exception as e:
        logger.error(f"Error sending status message: {e}")


async def find_lost_messages():
    """Finds all AirConditionerCommands that don't have a corresponding TemperatureSensorMessage."""
    status_messages_air_con_ids = [status_message.aircon_command.id for status_message in
                                   await StatusMessage.objects.all()]
    logger.debug(f'Status messages air con ids {status_messages_air_con_ids}')
    lost_commands = await AirConditionerCommand.objects.exclude(id__in=status_messages_air_con_ids).all()
    logger.debug(f'Lost commands {lost_commands}')
    return lost_commands


@shared_task(ignore_result=True)
def process_lost_commands():
    """Processes lost commands in a non-blocking manner."""
    lost_commands = find_lost_messages()
    for lost_command in lost_commands:
        result = StatusMessage(aircon_command=lost_command, status="LOST")
        db.session.add(result)
        db.session.commit()
        logger.debug(f'Created status message result {result} for {lost_command}')
        send_status(lost_command.uid, "LOST")
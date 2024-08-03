import asyncio
import json

from werkzeug.exceptions import abort
from project import create_app, ext_celery
from flask import request, jsonify, current_app, Response, abort
from project.commands.models import *
from project.cache import cache

from project.commands.tasks import send_status, process_lost_commands

app = create_app()
celery = ext_celery.celery

from flask_mqtt import Mqtt

mqtt = Mqtt(app)


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
                    # process_lost_commands()
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
                    status_message = StatusMessage(aircon_command_id=ac_command.id,
                                                   sensor_message_id=matching_message.id, status="MATCH")
                    current_app.logger.info("status_message.status is MATCH")
                else:
                    status_message = StatusMessage(aircon_command_id=ac_command.id,
                                                   sensor_message_id=matching_message.id,
                                                   status="MISMATCH")
                    current_app.logger.info("status_message.status is MISMATCH")
                current_app.logger.info(f'Creating status message {status_message}')
                db.session.add(status_message)
                db.session.commit()
                current_app.logger.info(f"Status message saved to database object is {status_message}")
                send_status.delay(ac_command.uid, status_message.status)
                # send_status(ac_command.uid, status_message.status)
            return Response("Command received", 201)
        except Exception as e:
            current_app.logger.error(f"Error processing ac command: {e}")
            abort(500, f"Error processing ac command: {e}")

# 
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('sensor/temperature')



@mqtt.on_message()
def sensor_temperature_handler(client, userdata, message):
    """
    Handles incoming temperature sensor messages from the MQTT topic "/sensor/temperature".

    Parses the message payload, creates a TemperatureSensorMessage model instance, saves it to the database,
    and checks for a matching AirConditionerCommand. If a match is found, it creates a StatusMessage
    with the appropriate status (MATCH, MISMATCH) and sends it to the Status service. If message payload is empty dict,
    it creates a StatusMessage with the status LOST and sends it to the Status service.


    Args:
        client (MQTTClient): The MQTT client instance.
        topic (str): The MQTT topic the message was received on.
        payload (bytes): The message payload.
        qos (int): The Quality of Service level for the message.
        properties (Any): Additional MQTT message properties.

    Raises:
        HTTPException: If there is an error parsing the message payload or processing the message.

    Returns:
        None
    """
    app.logger.debug(f'New message received with payload {message.payload}')
    try:
        data = json.loads(message.payload.decode())
    except Exception as e:
        app.logger.error("Error parsing message payload.".format(message.payload), exc_info=True)
        return
    if data:
        if cache.get(data['id']) == data['temp']:
            app.logger.debug(f"Message with {data['id']} already processed. Skipping.")
            return
        else:
            cache.set(data['id'], data['temp'], timeout=1800)
        try:
            # Create an AirConditionerCommand model instance
            with app.app_context():
                sensor_message = TemperatureSensorMessage(uid=data['id'], temperature=data['temp'])

                app.logger.info(f"Temperature sensor message is {sensor_message}")
                db.session.add(sensor_message)
                db.session.commit()
                app.logger.info(f"Temperature sensor message saved to database object is {sensor_message}")
                # Check for a matching message
                matching_ac_command = AirConCommand.query.filter_by(uid=sensor_message.uid).first()
                app.logger.info(f"Matching ac command is {matching_ac_command}")
                if matching_ac_command:
                    # Create a StatusMessage model instance
                    if matching_ac_command.temperature == sensor_message.temperature:
                        status_message = StatusMessage(aircon_command_id=matching_ac_command.id,
                                                       sensor_message_id=sensor_message.id, status="MATCH")
                        app.logger.info("status_message.status is MATCH")
                    else:
                        status_message = StatusMessage(aircon_command_id=matching_ac_command.id,
                                                       sensor_message_id=sensor_message.id,
                                                       status="MISMATCH")

                    db.session.add(status_message)
                    db.session.commit()
                    app.logger.info(f"Saved status_message to DB with result {status_message}")
                    send_status.delay(sensor_message.uid, status_message.status)
                    # send_status(sensor_message.uid, status_message.status)
        except KeyError:
            app.logger.error(f"Invalid message payload: {data}")
            return
        except Exception:
            app.logger.error('Error processing temperature sensor message with data {}'.format(data))
            return
    else:
        # Last message received
        app.logger.info('Empty payload indicates last message received. Start processing unmatched data.')
        last_ac_message = cache.get("ac_last_message")
        if last_ac_message:
            app.logger.info(f'Last ac message found {last_ac_message}')
            # Create a task to process lost commands in the background
            process_lost_commands.delay()
            # process_lost_commands()
            cache.delete("ac_last_message")
        else:
            app.logger.info(f'No last ac message found, saving last temperature sensor message')
            cache.set("t_sensor_last_message", True, timeout=1800)
            app.logger.debug(f"Last Temp Sensor message saved to cache {cache.get('t_sensor_last_message')}")
        return

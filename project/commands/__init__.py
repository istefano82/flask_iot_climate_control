from flask import Blueprint

commands_blueprint = Blueprint("commands", __name__, url_prefix="/commands", template_folder="templates")

from . import models  # noqa
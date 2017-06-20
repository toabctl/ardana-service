from flask import Blueprint
import logging

LOG = logging.getLogger(__name__)

bp = Blueprint('tasks', __name__)


@bp.route("/tasks/<id>")
def get_task(id):
    pass

from flask import abort, Blueprint, jsonify, request, \
    send_from_directory, url_for
import logging
import os


LOG = logging.getLogger(__name__)

bp = Blueprint('templates', __name__)

# TODO(gary): read this configuration from a config file
TEMPLATES_DIR = os.path.expanduser("~/dev/scratch/ansible/next/hos/ansible")
LOGS_DIR = "/projects/logs"

@bp.route("/api/v2/templates")
def get_all_templates():
    templates = []
    return jsonify(sorted(templates))

@bp.route("/api/v2/templates/<name>")
def get_template(name):
    template = {}
    return jsonify(sorted(template))

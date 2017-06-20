from flask import Blueprint, jsonify
import pbr.version
import time

bp = Blueprint('admin', __name__)


@bp.route("/v2/version")
def version():
    version_info = pbr.version.VersionInfo('ardana-server')
    return version_info.version_string()


@bp.route("/v2/heartbeat")
def heartbeat():
    # return ms since epoch
    return jsonify(int(1000 * time.time()))

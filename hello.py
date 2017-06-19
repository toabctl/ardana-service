from flask import abort
from flask import Flask
from flask import jsonify
from flask import request
import logging
import pbr.version
import re
import os
import time

LOG = logging.getLogger(__name__)
app = Flask(__name__)

# TODO: read playbooks_dir from config file
PLAYBOOKS_DIR = "/data/home/dev/scratch/ansible/next/hos/ansible"


@app.route("/version")
def version():
    version_info = pbr.version.VersionInfo('ardana-server')
    return version_info.version_string()


@app.route("/heartbeat")
def heartbeat():
    # return ms since epoch
    return jsonify(int(1000 * time.time()))


# TODO: Move the rest of this to another file
@app.route("/playbooks")
def playbooks():

    yml_re = re.compile(r'\.yml$')
    playbooks = {'config-processor-run',
                 'config-processor-clean',
                 'ready-deployment'}

    try:
        for filename in os.listdir(PLAYBOOKS_DIR):
            if filename[0] != '_' and yml_re.search(filename):
                # Strip off extension
                playbooks.add(filename[:-4])
    except OSError:
        LOG.warning("Playbooks directory %s doesn't exist. This could indicate"
                    " that the ready_deployment playbook hasn't been run yet. "
                    "The list of playbooks available will be reduced",
                    PLAYBOOKS_DIR)

    return jsonify(sorted(playbooks))


def get_extra_vars(opts):
    """
    In the JSON request payload, the special key extraVars wil be converted to
    the --extra-vars playbook argument, and it undergoes special processing.
    The supplied value will either be an array of key value pairs, e.g.
    ["key1=val1", "key2=val2"], or a nested object, e.g., { "key1": "val1",
    "key2": "val2" }
    """

    if type(opts.get("extraVars")) is list:
        d = {}
        for keyval in opts["extraVars"]:
            try:
                (key, val) = keyval.split("=", 1)
                d[key] = val
            except ValueError:
                pass
        return d
    else:
        return opts.get("extraVars", {})


def run_site(opts, client_id):
    pass


def run_config_processor_clean(opts, client_id):
    pass


def run_config_processor(opts, client_id):
    pass


def run_ready_deployment(opts, client_id):
    pass


@app.route("/playbook/<name>", methods=['POST'])
def run_playbook(name):
    """
    Run an ansible playbook

    JSON payload is an object that may contain key/value pairs that will be
    passed as command-line arguments to the ansible playbook.

    If the http header "hlmclientid" is supplied, it will be passed as
    a command-line argument named hlmClientId.
    """
    opts = request.get_json() or {}

    client_id = request.headers.get('hlmclientid')   # TODO Remove "hlm" here

    if name == "site":
        return run_site(opts, client_id)
    elif name == "config-processor-run":
        return run_config_processor(opts, client_id)
    elif name == "config-processor-clean":
        return run_config_processor_clean(opts, client_id)
    elif name == "ready-deployment":
        return run_ready_deployment(opts, client_id)
    else:
        try:
            name += ".yml"
            for filename in os.listdir(PLAYBOOKS_DIR):
                if filename == name:
                    break
            else:
                abort(404)

        except OSError:
            LOG.warning("Playbooks directory %s doesn't exist. This could "
                        "indicate that the ready_deployment playbook hasn't "
                        "been run yet. The list of playbooks available will "
                        "be reduced", PLAYBOOKS_DIR)

    return jsonify(opts)


if __name__ == "__main__":
    app.run(debug=True)

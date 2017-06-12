from flask import abort
from flask import Flask
from flask import jsonify
from flask import request
import logging
import pbr.version
import pdb
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
        LOG.warning("Playbooks directory %s doesn't exist. " \
            "This could indicate that the ready_deployment playbook hasn't been run yet. " \
            "The list of playbooks available will be reduced", PLAYBOOKS_DIR);

    return jsonify(sorted(playbooks))


@app.route("/playbook/<name>", methods=['POST'])
def run_playbook(name):
    """
    Run an ansible playbook

    JSON payload is an object that may contain key/value pairs that will be
    passed as command-line arguments to the ansible playbook.  

    The special key extraVars wil be converted to the --extra-vars playbook
    argument, and it undergoes special processing.  The supplied value will
    either be an array of key value pairs, e.g. ["key1=val1", "key2=val2"], or
    a nested object, e.g., { "key1": "val1", "key2": "val2" }
    
    If the http header "hlmclientid" is supplied, it will be passed as
    a command-line argument named hlmClientId.
    """
    opts = request.get_json()

    if opts:
        # TODO: This is stupid and ugly.  The process manager handles 
        # strips this "option" away and handles it todally differently.
        # It should be treated as a different beast rather than putting
        # it in "opts"
        opts['hlmClientId'] = request.headers.get('hlmclientid')

        if type(opts.get("extraVars")) is list:
            d = {}
            for keyval in opts["extraVars"]:
                try:
                    (key, val) = keyval.split("=", 1)
                    d[key] = val
                except ValueError:
                    pass
            opts["extraVars"] = d

    try:
        name += ".yml"
        for filename in os.listdir(PLAYBOOKS_DIR):
            if filename == name:
                break
        else:
            abort(404)

    except OSError:
        LOG.warning("Playbooks directory %s doesn't exist. " \
            "This could indicate that the ready_deployment playbook hasn't been run yet. " \
            "The list of playbooks available will be reduced", PLAYBOOKS_DIR);

    return jsonify(opts)


if __name__ == "__main__":
    app.run(debug=True)

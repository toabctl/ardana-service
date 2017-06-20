from flask import abort, Blueprint, jsonify, request, url_for
import logging
import os
import re
import subprocess
import threading
import time

LOG = logging.getLogger(__name__)

bp = Blueprint('playbooks', __name__)

# TODO(gary): read playbooks_dir from config file
PLAYBOOKS_DIR = "/data/home/dev/scratch/ansible/next/hos/ansible"

# Dictionary of all running tasks
tasks = {}


@bp.route("/playbooks")
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

    # In the JSON request payload, the special key extraVars wil be converted
    # to the --extra-vars playbook argument, and it undergoes special
    # processing.  The supplied value will either be an array of key value
    # pairs, e.g.  ["key1=val1", "key2=val2"], or a nested object, e.g.,
    # { "key1": "val1", "key2": "val2" }
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

    # Normalize the extraVars entry
    opts['extraVars'] = get_extra_vars(opts)

    keep_dayzero = opts['extraVars'].pop('keep_dayzero', None)
    destroy_on_success = opts.pop('destroyDayZeroOnSuccess', None)

    # TODO(gary): Handle things like reading passwords from an encrypted vault
    # TODO(gary): if successful and destory_on_success, then invoke
    # dayzero-stop playbook


def run_config_processor_clean(opts, client_id):
    pass


def run_config_processor(opts, client_id):
    pass


def run_ready_deployment(opts, client_id):
    pass


@bp.route("/playbook/<name>", methods=['POST'])
def run_playbook(name):
    """
    Run an ansible playbook

    JSON payload is an object that may contain key/value pairs that will be
    passed as command-line arguments to the ansible playbook.

    If the http header "clientid" is supplied, it will be passed as
    a command-line argument named ClientId.
    """
    opts = request.get_json() or {}

    client_id = request.headers.get('clientid')   # TODO(gary) Remove "hlm"

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

            return spawn_process('/projects/blather', ["10"])

        except OSError:
            LOG.warning("Playbooks directory %s doesn't exist. This could "
                        "indicate that the ready_deployment playbook hasn't "
                        "been run yet. The list of playbooks available will "
                        "be reduced", PLAYBOOKS_DIR)

    return jsonify(opts)


def read_process_output(ps):

    with ps.stdout:
        for line in ps.stdout:
            # python 2 returns bytes that must be converted to a string
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            line = line.rstrip('\n')
            print(line)
    ps.wait()


def spawn_process(command, args=[], cwd=None, opts={}):

    # TODO(gary): Add logic to avoid spawning duplicate playbooks when
    # indicated, by looking at all running playbooks for one with the same
    # command line

    cmdArgs = [command]
    cmdArgs.extend(args)

    try:
        ps = subprocess.Popen(cmdArgs, cwd=cwd, env=opts.get('env', None),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        pass

    start_time = int(1000 * time.time())

    id = "%d_%d" % (start_time, ps.pid)

    tasks[id] = {'task': threading.Thread(target=read_process_output,
                                          args=(ps,)),
                 'start_time': start_time}

    tasks[id]['task'].start()

    return '', 202, {'Location': url_for('tasks.get_task', id=id)}

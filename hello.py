from flask import Flask
from flask import jsonify
import pbr.version
import re
import os
import time

app = Flask(__name__)


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
    # TODO: read playbooks_dir from config file
    playbooks_dir = "/data/home/dev/scratch/ansible/next/hos/ansible"

    yml_re = re.compile(r'\.yml$')

    playbooks = {'config-processor-run',
                 'config-processor-clean',
                 'ready-deployment'}
    for filename in os.listdir(playbooks_dir):
        if filename[0] != '_' and yml_re.search(filename):
            # Strip off extension
            playbooks.add(filename[:-4])

    return jsonify(sorted(playbooks))


if __name__ == "__main__":
    app.run(debug=True)

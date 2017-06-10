from flask import Flask
import time
import pbr.version

app = Flask(__name__)


@app.route("/version")
def version():
    version_info = pbr.version.VersionInfo('ardana-server')
    return version_info.version_string()


@app.route("/heartbeat")
def heartbeat():
    # return ms since epoch
    return str(int(1000 * time.time()))


if __name__ == "__main__":
    app.run()

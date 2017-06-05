from flask import Flask
import time
app = Flask(__name__)


@app.route("/heartbeat")
def heartbeat():
    return str(time.time())


if __name__ == "__main__":
    app.run()

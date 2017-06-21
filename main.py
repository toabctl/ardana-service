from flask import Flask
from flask_socketio import SocketIO
from ardana_server import playbooks, admin, tasks, socketio
import logging

LOG = logging.getLogger(__name__)
app = Flask(__name__)
app.register_blueprint(admin.bp)
app.register_blueprint(playbooks.bp)
app.register_blueprint(tasks.bp)

if __name__ == "__main__":
    # app.run(debug=True)
    socketio.init_app(app)
    socketio.run(app, use_reloader=True)

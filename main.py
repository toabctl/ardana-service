from ardana_service import admin
from ardana_service import model
from ardana_service import playbooks
from ardana_service import socketio
from ardana_service import tasks
from flask import Flask
import logging
logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger(__name__)
app = Flask(__name__)
app.register_blueprint(admin.bp)
app.register_blueprint(playbooks.bp)
app.register_blueprint(tasks.bp)
app.register_blueprint(model.bp)

if __name__ == "__main__":
    # app.run(debug=True)
    socketio.init_app(app)
    socketio.run(app, use_reloader=True)

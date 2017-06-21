from flask_socketio import SocketIO

socketio = SocketIO()

# Import any modules that refer to socketio here (after socketio has been
# created)
from . import playbooks

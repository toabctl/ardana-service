from flask_socketio import SocketIO

# For some reason, the default async mode of eventlet causes the main 
#   thread to pause while the background thread runs. Yuck
socketio = SocketIO(async_mode="threading")

# Import any modules that refer to socketio here (after socketio has been
# created)
from . import playbooks

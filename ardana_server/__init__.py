from flask_socketio import SocketIO

# For some reason, the default async mode (eventlet) causes the main 
#   thread to pause while the background thread runs. The "threading"
#   option works fine in dev mode, but only supports long polling
#   (not WebSockets).
socketio = SocketIO() # async_mode="threading")

# Import any modules that refer to socketio here (after socketio has been
# created)
from . import playbooks

import logging
from socketIO_client import SocketIO, LoggingNamespace

logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()


def on_connect():
    print('connect')

def on_disconnect():
    print('disconnect')

def on_reconnect():
    print('reconnect')

def on_aaa_response(*args):
    print('on_aaa_response', args)

socketIO = SocketIO('localhost', 5000, LoggingNamespace)
socketIO.on('connect', on_connect)
socketIO.on('disconnect', on_disconnect)
socketIO.on('reconnect', on_reconnect)

socketIO.wait(seconds=10)

## Listen
#socketIO.on('aaa_response', on_aaa_response)
#socketIO.emit('aaa')
#socketIO.emit('aaa')
#socketIO.wait(seconds=1)
#
## Stop listening
#socketIO.off('aaa_response')
#socketIO.emit('aaa')
#socketIO.wait(seconds=1)
#
## Listen only once
#socketIO.once('aaa_response', on_aaa_response)
#socketIO.emit('aaa')  # Activate aaa_response
#socketIO.emit('aaa')  # Ignore
#socketIO.wait(seconds=1)
#

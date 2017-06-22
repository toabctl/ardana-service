import logging
import json
import requests

from socketIO_client import SocketIO, BaseNamespace, LoggingNamespace

logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

def on_message(message):
    # message is a json-formatted string of args prefixed with '2' 
    # (which means it is an event), plus any namespace.  So, if
    # the message is in the /log namespace, it will be in the format 
    # 2/log["the message"]
    args = json.loads(message.lstrip('2'))
    print "LOG: ", args[1]

socketIO = SocketIO('localhost', 5000, LoggingNamespace)

socketIO.on('message', on_message)  # , path='/log')

print "Posting request"
r = requests.post("http://localhost:5000/v2/playbooks/x.yml")
id = r.headers['Location'].split('/')[-1]

print "Joining room", id
socketIO.emit('join', id)   # , path="/log")
print "Joined room", id

print "Reading messages"
socketIO.wait(seconds=6)


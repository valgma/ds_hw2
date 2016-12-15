#!/usr/bin/env python
import sys
from server import Server
from utils import make_logger
import uuid
Log = make_logger()

"""
Checking if the external IP is set
"""
if len(sys.argv) > 2:
    ext_host = sys.argv[2]
else:
    ext_host = 'localhost'

"""
And the internal one to which we bind the socket.
"""
if len(sys.argv) > 1:
    pikahost = sys.argv[1]
else:
    pikahost = 'localhost'

"""
This is a hacky way of setting up "unique" server names without having to
manually do it
"""
name = "server_"+str(uuid.uuid1())
s = Server(pikahost,name,ext_host)
try:
    s.run()
except KeyboardInterrupt:
    print "Control-c, shutting down.."

s.disconnect()

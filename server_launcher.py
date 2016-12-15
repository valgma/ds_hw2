#!/usr/bin/env python
import sys
from random import randint
from server import Server
from utils import make_logger
Log = make_logger()

if len(sys.argv) > 2:
    ext_host = sys.argv[2]
else:
    ext_host = 'localhost'

if len(sys.argv) > 1:
    pikahost = sys.argv[1]
else:
    pikahost = 'localhost'

name = "server_"+str(randint(0,1000))
s = Server(pikahost,name,ext_host)
try:
    s.run()
except KeyboardInterrupt:
    print "Control-c, shutting down.."

s.disconnect()

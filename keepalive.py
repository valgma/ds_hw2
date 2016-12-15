from utils import TIMEOUT, KEEPALIVE, make_logger
from threading import Thread, Event
from time import sleep

Log = make_logger()

class KeepAliveListener(Thread):
    def __init__(self,channel,exchange):
        Thread.__init__(self)
        self.clients = {}
        self.channel = channel
        self.to_exchange = exchange

    def run(self):
        while 1:
            sleep(TIMEOUT)
            alive = {}
            print "<<<<< WIPE >>>>>"
            for client in self.clients.keys():
                client_event = self.clients[client]
                if not client_event.is_set():
                    Log.info("%r has disconnected from exchange" % client)
                    self.notify_exchange(self.to_exchange,"players.disconnected",client)
                else:
                    print "%r is alive" % client
                    alive[client] = client_event
                    alive[client].clear()
            print "<<<<< WIPE >>>>>"
            self.clients = alive

    def add_client(self,client):
        if client not in self.clients.keys():
            self.clients[client] = Event()
            self.clients[client].set()

    def poke_client(self,client):
        self.clients[client].set()

    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.info("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.info("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

class KeepAliveSpammer(Thread):
    def __init__(self,channel,exchange,name):
        Thread.__init__(self)
        self.channel = channel
        self.to_exchange = exchange
        self.username = name
        self.stopEvent = Event()

    def run(self):
        while not self.stopEvent.is_set():
            sleep(KEEPALIVE)
            self.notify_exchange(self.to_exchange,"players.alive",self.username)

    def stop(self):
        self.stopEvent.set()

    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.info("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.info("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

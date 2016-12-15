from utils import TIMEOUT, KEEPALIVE, make_logger
from threading import Thread, Event
from time import sleep

Log = make_logger()

"""
A thread which keeps track of how long someone has not notified us of
their existence. If they don't do it for long enough, this thread also notifies
everyone that they have disconnected.
"""
class KeepAliveListener(Thread):
    """
    The constructor
    @param channel - the channel to use for transmission
    @param exchange - the exchange that should be notified of disconnects
    """
    def __init__(self,channel,exchange):
        Thread.__init__(self)
        self.clients = {}
        self.channel = channel
        self.to_exchange = exchange

    """
    The main loop of the thread.
    It sleeps for a little while, then checks the events linked with every
    client. If the event is not set then the client has not notified us about
    themselves in the span of the timeout and the server will be notified of
    his disappearance. Otherwise we reset the events so that everyone has to
    notify themselves again.
    """
    def run(self):
        while 1:
            sleep(TIMEOUT)
            alive = {}
            for client in self.clients.keys():
                client_event = self.clients[client]
                if not client_event.is_set():
                    Log.info("%r has disconnected from exchange" % client)
                    self.notify_exchange(self.to_exchange,"players.disconnected",client)
                else:
                    alive[client] = client_event
                    alive[client].clear()
            Log.info("%d clients still alive" % len(alive.keys()))
            self.clients = alive

    """
    Just adding an extra client to the handler
    @param client - the client to be added
    """
    def add_client(self,client):
        if client not in self.clients.keys():
            self.clients[client] = Event()
            self.clients[client].set()

    """
    The method where clients that are already accounted for extend their time
    to live by triggering the event. This buys them another cycle's worth of
    time.+
    """
    def poke_client(self,client):
        try:
            self.clients[client].set()
        except KeyError as e:
            return

    """
    The wrapper for sending messages that I've been using for a while.
    """
    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.info("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.info("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

"""
The above class listens to messages sent by this class, which periodically
sends updates that a client has not disconnected.
"""
class KeepAliveSpammer(Thread):
    """
    The constructor
    @param channel - the pika channel for transmission
    @param exchange - the exchange that needs to be notified constantly
    @param name - the person who is (hopefully) alive
    """
    def __init__(self,channel,exchange,name):
        Thread.__init__(self)
        self.channel = channel
        self.to_exchange = exchange
        self.username = name
        self.stopEvent = Event()

    """
    The main loop of the thread - it just sends a message at a fixed interval
    """
    def run(self):
        while not self.stopEvent.is_set():
            sleep(KEEPALIVE)
            self.notify_exchange(self.to_exchange,"players.alive",self.username)

    """
    Since the clients can change servers, the thread has to be stoppable.
    """
    def stop(self):
        self.stopEvent.set()

    """
    The wrapper for sending messages that I've been using for a while.
    """
    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.info("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.info("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

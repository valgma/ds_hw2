#!/usr/bin/env python
#from utils import make_logger
import pika
from gameroom import Gameroom
from utils import make_logger, SERV_EXCHANGE, DELIM
from threading import Thread
from gamestate import GameState
from keepalive import KeepAliveListener
import Pyro4

Log = make_logger()

GAME_KEYS = ["players.req","players.ping","players.remove","gameroom.request","gameroom.remove","gameroom.ping",\
                "gameroom.join","players.disconnected","players.alive"]
SERVER_KEYS = ["ping_open"]

"""
The main server class
"""
class Server():
    """
    @param pikahost - the rabbitmq server
    @param title - the server's name
    @param external_host - the server's external IP
    """
    def __init__(self,pikahost,title,external_host):
        self.servname = title
        self.host = pikahost
        self.connected_clients = []
        self.connect(pikahost)

        self.kal = KeepAliveListener(self.channel,self.servname)
        self.kal.setDaemon(True)
        self.kal.start()

        self.gamerooms = {}
        self.objects = {}
        self.object_handler = ObjectHandler(pikahost,external_host)
        self.object_handler.setDaemon(True)
        self.object_handler.start()

    """
    Initializing the connection
    @param pikahost - the rabbitmq server
    """
    def connect(self,pikahost):
        #connect to broker
        credentials = pika.PlainCredentials('DSHW2', 'DSHW2')
        parameters = pika.ConnectionParameters(pikahost,5672,'/',credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        self.declare_exchanges()
        self.make_queues()
        #bind queues to relevant topics, specify what is consumed where
        self.bind_queues()
        #publish own channel in servers
        self.publish_status(True)

    """
    Initializing the exchanges. The exchange that the server uses is the same
    as its name.
    """
    def declare_exchanges(self):
        self.channel.exchange_declare(exchange=SERV_EXCHANGE,type='direct')
        #create server exchange
        self.channel.exchange_declare(exchange=self.servname,type='direct')

    """
    Initializing the queues
    Again we have different types of queues
    The server queue, which handles the comings and goings of servers
    The lobby queue, where rooms and players come and go
    """
    def make_queues(self):
        #create lobby queue
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.lobby_queue = self.dec_result.method.queue

        self.lobby_reply_prop = pika.BasicProperties(reply_to = self.lobby_queue)
        #create game queue
        self.game_dec = self.channel.queue_declare(exclusive=True)
        self.game_queue = self.game_dec.method.queue

    """
    Initializing all the queue bindings of the routing keys
    """
    def bind_queues(self):
        #listen to clients asking for server list
        for k in SERVER_KEYS:
            self.channel.queue_bind(exchange=SERV_EXCHANGE,
                                    queue=self.lobby_queue,
                                    routing_key=k)

        #listen to own server exchange
        for k in GAME_KEYS:
            self.channel.queue_bind(exchange=self.servname,
                                    queue=self.game_queue,
                                    routing_key=k)

        #What queue is processed where
        self.channel.basic_consume(self.lobby_queue_callback,
                      queue=self.lobby_queue,
                      no_ack=True)
        self.channel.basic_consume(self.game_queue_callback,
                        queue=self.game_queue)

    """
    The main lobby callback method (nevermind the name).
    This handles events regarding the comings/goings of servers and players.
    Also handles player and room join/creation requests.
    """
    def game_queue_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.info("Lobby queue received message %r with key %r" % (body,rk))

        if rk == 'players.req':
            target = properties.reply_to
            if body not in self.connected_clients:
                self.connected_clients.append(body)
                self.notify_exchange(self.servname,'players.add',body)
                self.notify_exchange('',target,'players.confirm'+DELIM+self.servname+DELIM+body)
                self.kal.add_client(body)
            else:
                self.notify_exchange('',target,'players.reject'+DELIM+self.servname+DELIM+body)
        elif rk == 'players.remove':
            try:
                self.connected_clients.remove(body)
            except:
                pass
        elif rk == "players.disconnected":
            self.notify_exchange(self.servname,'players.remove',body)
        elif rk == "players.alive":
            self.kal.poke_client(body)
        elif rk == 'gameroom.request':
            pieces = body.split("/")
            name = pieces[0]
            board_size = int(pieces[1])
            if name not in self.gamerooms.keys():
                gs = GameState(board_size)
                self.objects[name] = gs
                uri = self.object_handler.register(gs)
                print uri
                rm = Gameroom(self.host,name,self,gs,uri)
                rm.setDaemon(True)
                rm.start()
                self.gamerooms[name] = rm
                returnaddr = properties.reply_to
                message = "gameroom.confirm"+DELIM+name
                self.notify_exchange('',returnaddr,message)
                self.notify_exchange(self.servname,'gameroom.add',name)
        elif rk == 'gameroom.ping':
            for rm in self.gamerooms.keys():
                self.notify_exchange(self.servname,'gameroom.add',rm)
                if not self.gamerooms[rm].open:
                    self.notify_exchange(self.servname,'gameroom.busy',rm)
        elif rk == 'gameroom.join':
            m = body.split(DELIM)
            room_name = m[0]
            user_name = m[1]
            if room_name in self.gamerooms.keys():
                room = self.gamerooms[room_name]
                returnaddr = properties.reply_to
                print room.open
                print room.players
                if room.open or user_name in room.players:
                    message = "gameroom.confirm"+DELIM+room_name
                else:
                    message = "gameroom.reject"+DELIM+room_name
                self.notify_exchange('',returnaddr,message)

    """
    A wrapper with a log function stuck to it.
    """
    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.info("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.info("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

    """
    The server callback function, where nothing much really happens.
    """
    def lobby_queue_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.info("Lobby queue received message %r with key %r." % (body,rk))
        if rk == 'ping_open':
            self.publish_status(True)

    """
    legacy code, which could really be cut down, but it's 11 am..
    """
    def publish_status(self,running):
        tag = 'open' if running else 'closed'
        self.notify_exchange(SERV_EXCHANGE,tag,self.servname,self.lobby_reply_prop)

    """
    A function which destroys a game room once everyone has left it.
    @param roomname - the room to be destroyed
    """
    def destroy_room(self,roomname):
        try:
            self.gamerooms[roomname].disconnect()
            del self.gamerooms[roomname]
            self.object_handler.unregister(objects[roomname])
            del objects[roomname]
        except:
            return

    """
    The main loop of the server
    """
    def run(self):
        self.channel.start_consuming()

    """
    And of course disconnecting/clearing stuff
    """
    def disconnect(self):
        self.channel.exchange_delete(self.servname)
        self.publish_status(False)
        self.channel.close()

"""
A thread which handles all the pyro4 daemon registering
"""
class ObjectHandler(Thread):
    """
    @param servhost - the IP that the server is bound to
    @param nathost - the external IP of the server
    """
    def __init__(self,servhost,external_host):
        Thread.__init__(self)
        self.pyro_daemon = Pyro4.Daemon(host=servhost,port=7777,nathost=external_host,natport=7777)

    """
    The main loop - just a request loop
    """
    def run(self):
        self.pyro_daemon.requestLoop()

    """
    All other functions are just wrappers really.
    """
    def register(self,inc):
        return self.pyro_daemon.register(inc)

    def geturi(self,inc):
        return self.pyro_daemon.geturi(inc)

    def unregister(self,inc):
        return self.pyro_daemon.unregister(inc)

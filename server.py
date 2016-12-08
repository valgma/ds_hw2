#!/usr/bin/env python
#from utils import make_logger
import pika
from gameroom import Gameroom
from utils import make_logger, SERV_EXCHANGE, DELIM

Log = make_logger()

GAME_KEYS = ["players.req","players.ping","players.remove","gameroom.add","gameroom.remove","gameroom.ping"]
SERVER_KEYS = ["ping_open"]

class Server():
    def __init__(self,pikahost,title):
        self.servname = title
        self.host = pikahost
        self.connected_clients = []
        self.connect(pikahost)
        self.rooms = {}

    def connect(self,pikahost):
        #connect to broker
        #TODO: Actually connect outside of localhost
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=pikahost))
        self.channel = self.connection.channel()

        self.declare_exchanges()
        self.make_queues()
        #bind queues to relevant topics, specify what is consumed where
        self.bind_queues()
        #publish own channel in servers
        self.publish_status(True)

    def declare_exchanges(self):
        self.channel.exchange_declare(exchange=SERV_EXCHANGE,type='direct')
        #create server exchange
        self.channel.exchange_declare(exchange=self.servname,type='direct')

    def make_queues(self):
        #create lobby queue
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.lobby_queue = self.dec_result.method.queue

        self.lobby_reply_prop = pika.BasicProperties(reply_to = self.lobby_queue)
        #create game queue
        self.game_dec = self.channel.queue_declare(exclusive=True)
        self.game_queue = self.game_dec.method.queue

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

    def game_queue_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Game queue received message %r with key %r" % (body,rk))

        if rk == 'players.req':
            if body not in self.connected_clients:
                self.connected_clients.append(body)
                target_queue = properties.reply_to
                self.accept_player(body,target_queue)

        elif rk == 'players.ping':
            for player in self.connected_clients:
                self.notify_exchange(self.servname,'players.add',player)

        elif rk == 'players.remove':
            try:
                self.connected_clients.remove(body)
            except:
                pass
        elif rk == 'gameroom.add':
            if body not in self.rooms.keys():
                rm = Gameroom(self.host,body,self.servname)
                rm.setDaemon(True)
                rm.start()
                self.rooms[body] = rm
                returnaddr = properties.reply_to
                message = "gameroom.confirm"+DELIM+body
                self.notify_exchange('',returnaddr,message)
        elif rk == 'gameroom.ping':
            for rm in self.rooms.keys():
                self.notify_exchange(self.servname,'gameroom.add',rm)

    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.debug("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.debug("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

    def accept_player(self,player_name,target):
        self.notify_exchange(self.servname,'players.add',player_name)
        self.notify_exchange('',target,'players.confirm'+DELIM+self.servname+DELIM+player_name)

    def lobby_queue_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Lobby queue received message %r with key %r." % (body,rk))
        if rk == 'ping_open':
            self.publish_status(True)

    def publish_status(self,running):
        tag = 'open' if running else 'closed'
        self.notify_exchange(SERV_EXCHANGE,tag,self.servname,self.lobby_reply_prop)

    def run(self):
        self.channel.start_consuming()

    def disconnect(self):
        self.channel.exchange_delete(self.servname)
        self.publish_status(False)
        self.channel.close()

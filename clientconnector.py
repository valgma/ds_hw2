#!/usr/bin/env python
from utils import make_logger, SERV_EXCHANGE
from threading import Thread

import pika

GAME_KEYS = ["players.add", "players.remove"]
SERVER_KEYS = []
Log = make_logger()
#TODO: Field for ":" and other magic strings

class ClientConnector(Thread):
    def __init__(self,pikahost,client):
        Thread.__init__(self)
        self.app = client
        self.game_server = ""
        self.connect(pikahost)
        self.ping_servers()

    def connect(self,pikahost):
        #connect to broker
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=pikahost))
        self.channel = self.connection.channel()
        #connect to server declaration exchange
        self.channel.exchange_declare(exchange=SERV_EXCHANGE,type='direct')
        self.make_queues()
        self.set_server_subscriptions(True)

        self.channel.basic_consume(self.callback,
                              queue=self.lobby_queue,
                              no_ack=True)
        #self.channel.basic_qos(prefetch_count=1)

    def make_queues(self):
        #create own message queues
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.lobby_queue = self.dec_result.method.queue
        self.lobby_reply_prop = pika.BasicProperties(reply_to = self.lobby_queue)

        self.game_dec = self.channel.queue_declare(exclusive=False)
        self.game_queue = self.game_dec.method.queue

    def set_server_subscriptions(self,add):
        #listen/forget new declarations of open servers and closing servers
        if add:
            self.channel.queue_bind(exchange=SERV_EXCHANGE,
                               queue=self.lobby_queue,
                               routing_key='open')
            self.channel.queue_bind(exchange=SERV_EXCHANGE,
                                  queue=self.lobby_queue,
                                  routing_key='closed')
        else:
            self.channel.queue_unbind(exchange=SERV_EXCHANGE,
                               queue=self.lobby_queue,
                               routing_key='open')
            self.channel.queue_unbind(exchange=SERV_EXCHANGE,
                                  queue=self.lobby_queue,
                                  routing_key='closed')

    def ping_servers(self):
        self.notify_exchange(SERV_EXCHANGE,'ping_open','',self.lobby_reply_prop)

    def run(self):
        self.channel.start_consuming()

    def callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Lobby queue received message %r with key %r." % (body,rk))
        if rk == 'open':
            self.app.update_server_box(body,True)
        elif rk == 'closed':
            self.app.update_server_box(body,False)
        elif body.startswith("players.add"):
            msg = body.split(":",2)
            server_name = msg[1]
            self.connect_game_exchange(server_name)
            self.set_server_subscriptions(False)
            self.app.username = msg[2]
            self.app.show_lobby()

    def connect_game_exchange(self,server_name):
        for key in GAME_KEYS:
            self.channel.queue_bind(exchange=server_name,
                                    queue=self.game_queue,
                                    routing_key=key)
        self.channel.basic_consume(self.game_callback,
                                queue=self.game_queue)
        self.game_server = server_name

    def game_callback(self, ch, method, properties, body):
        rk = method.routing_key
        if rk == 'players.add':
            self.app.update_client_box(body,True)
        elif rk == 'players.remove':
            self.app.update_client_box(body,False)

    def join_server(self,serv_name,username):
        self.propose_name(serv_name,username)

    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.debug("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.debug("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

    def notify_game_server(self,key,message,props=None):
        self.notify_exchange(self.game_server,key,message,props)

    def propose_name(self,serv_name,username):
        self.channel.exchange_declare(exchange=serv_name,type='direct')
        self.notify_exchange(serv_name,'players.req',username,self.lobby_reply_prop)

    def request_playerlist(self):
        self.notify_game_server('players.ping','')

    def disconnect(self):
        if self.app.username:
            self.notify_game_server('players.remove',self.app.username)
        self.channel.queue_delete(queue=self.lobby_queue)
        self.connection.close()

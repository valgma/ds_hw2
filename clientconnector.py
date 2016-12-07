#!/usr/bin/env python
from utils import make_logger, SERV_EXCHANGE, DELIM
from threading import Thread

import pika

LOBBY_KEYS = ["players.add", "players.remove","gameroom.add","gameroom.remove"]
SERVER_KEYS = []
Log = make_logger()
GAME_KEYS = ["game.next","game.leader","game.joined","game.left"]
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
        self.make_queues()
        self.set_server_subscriptions(True)

        self.channel.basic_consume(self.server_callback,
                              queue=self.lobby_queue,
                              no_ack=True)
        #self.channel.basic_qos(prefetch_count=1)

    def make_queues(self):
        #create own message queues
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.lobby_queue = self.dec_result.method.queue
        self.lobby_reply_prop = pika.BasicProperties(reply_to = self.lobby_queue)

        self.game_dec = self.channel.queue_declare(exclusive=True)
        self.game_queue = self.game_dec.method.queue

        self.room_dec = self.channel.queue_declare(exclusive=True)
        self.room_queue = self.room_dec.method.queue

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

    def server_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Server queue received message %r with key %r." % (body,rk))
        if rk == 'open':
            self.app.update_server_box(body,True)
        elif rk == 'closed':
            self.app.update_server_box(body,False)
        elif body.startswith("players.confirm"):
            msg = body.split(DELIM,2)
            server_name = msg[1]
            self.connect_game_exchange(server_name)
            self.set_server_subscriptions(False)
            self.app.username = msg[2]
            self.app.show_lobby()


    def connect_game_exchange(self,server_name):
        for key in LOBBY_KEYS:
            self.channel.queue_bind(exchange=server_name,
                                    queue=self.game_queue,
                                    routing_key=key)
        self.channel.basic_consume(self.lobby_callback,
                                queue=self.game_queue)
        self.game_server = server_name

    def join_room_exchange(self,room_name):
        for key in GAME_KEYS:
            self.channel.queue_bind(exchange=room_name,
                                    queue=self.room_queue,
                                    routing_key=key)
        self.channel.basic_consume(self.game_callback,queue=self.room_queue)

    def game_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Lobby queue received message %r with key %r." % (body,rk))

    def lobby_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Lobby queue received message %r with key %r." % (body,rk))
        if rk == 'players.add':
            self.app.update_client_box(body,True)
        elif rk == 'players.remove':
            self.app.update_client_box(body,False)
        elif rk == 'gameroom.add':
            self.app.update_listbox(self.app.lobby_roomlist,body,True)
        elif rk == 'gameroom.remove':
            self.app.update_listbox(self.app.lobby_roomlist,body,False)
        elif body.startswith("gameroom.confirm"):
            msg = body.split(DELIM)
            room_name = msg[1]
            #TODO: connect to queue
            self.app.hide_lobby()
            self.app.draw_game()
            self.join_room_exchange(self.game_server+DELIM+room_name)

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
        self.notify_exchange(serv_name,'players.req',username,self.lobby_reply_prop)

    def request_playerlist(self):
        self.notify_game_server('players.ping','')

    def request_room(self,name):
        replyprop = pika.BasicProperties(reply_to=self.game_queue)
        self.notify_game_server('gameroom.add',name,replyprop)

    def request_roomlist(self):
        self.notify_game_server('gameroom.ping','')

    def disconnect(self):
        if self.app.username:
            self.notify_game_server('players.remove',self.app.username)
        self.channel.queue_delete(queue=self.lobby_queue)
        self.connection.close()

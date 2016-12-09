#!/usr/bin/env python
from utils import make_logger, SERV_EXCHANGE, DELIM
from threading import Thread

import pika

LOBBY_KEYS = ["players.add", "players.remove","gameroom.add","gameroom.remove",\
    "players.busy","players.available","players.ping"]
SERVER_KEYS = ["open","closed"]
Log = make_logger()
GAME_KEYS = ["game.next","game.leader","game.joined","game.sayonara","game.uri","game.ping"]
#TODO: Field for ":" and other magic strings

class ClientConnector(Thread):
    def __init__(self,pikahost,client):
        Thread.__init__(self)
        self.app = client
        self.lobby_server = ""
        self.connect(pikahost)
        self.game_ui = None
        self.room_name = ""
        self.ping_servers()

    def connect(self,pikahost):
        #connect to broker
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=pikahost))
        self.channel = self.connection.channel()
        #connect to server declaration exchange
        self.make_queues()
        self.channel.exchange_declare(exchange=SERV_EXCHANGE,type='direct')
        self.connect_exchange(SERV_EXCHANGE,SERVER_KEYS,self.server_queue,True)

        self.channel.basic_consume(self.server_callback,
                              queue=self.server_queue,
                              no_ack=True)
        #self.channel.basic_qos(prefetch_count=1)

    def make_queues(self):
        #create own message queues
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.server_queue = self.dec_result.method.queue
        self.lobby_reply_prop = pika.BasicProperties(reply_to = self.server_queue)

        self.game_dec = self.channel.queue_declare(exclusive=True)
        self.lobby_queue = self.game_dec.method.queue

        self.room_dec = self.channel.queue_declare(exclusive=True)
        self.game_queue = self.room_dec.method.queue

        self.channel.basic_consume(self.lobby_callback,
                                queue=self.lobby_queue)
        self.channel.basic_consume(self.game_callback,queue=self.game_queue)

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
            self.lobby_server = server_name
            self.connect_exchange(server_name,LOBBY_KEYS,self.lobby_queue,True)
            self.app.username = msg[2]
            self.app.hide_server_selection()
            self.app.show_lobby()

    def connect_exchange(self,server_name,keys,q,connect):
        for key in keys:
            if connect:
                self.channel.queue_bind(exchange=server_name,
                                        queue=q,
                                        routing_key=key)
            else:
                self.channel.queue_unbind(exchange=server_name,
                                        queue=q,
                                        routing_key=key)

    def game_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Game queue received message %r with key %r." % (body,rk))
        if rk == "game.sayonara":
            self.game_ui.rem_player(body)
        elif rk == "game.joined":
            self.game_ui.add_player(body)
        elif rk == "game.uri":
            self.game_ui.connect_state(body)
        elif rk == "game.ping":
            self.notify_exchange(self.room_name,"game.joined",self.app.username)
            #can't put it on server side because it might be out of sync..
            if self.game_ui.leader == self.app.username:
                self.notify_exchange(self.room_name,"game.leader",self.app.username)
        elif rk == "game.leader":
            self.game_ui.promote_to_leader(body)

    def lobby_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Lobby queue received message %r with key %r." % (body,rk))
        if rk == 'players.add':
            self.app.update_client_box(body,True)
        elif rk == 'players.remove':
            self.app.update_client_box(body,False)
        elif rk == 'players.busy':
            self.app.mark_red(self.app.client_list,body,True)
        elif rk == 'players.available':
            self.app.mark_red(self.app.client_list,body,False)
        elif rk == 'gameroom.add':
            self.app.update_listbox(self.app.lobby_roomlist,body,True)
        elif rk == 'gameroom.remove':
            self.app.update_listbox(self.app.lobby_roomlist,body,False)
        elif rk == 'players.ping':
            self.notify_lobby_server('players.add',self.app.username)
            if self.game_ui:
                self.notify_lobby_server('players.busy',self.app.username)
        elif body.startswith("gameroom.confirm"):
            msg = body.split(DELIM)
            room_name = msg[1]
            self.room_name = self.lobby_server+DELIM+room_name
            self.connect_exchange(self.room_name,GAME_KEYS,self.game_queue,True)
            self.app.hide_lobby()
            self.app.draw_game()
            self.game_ui = self.app.game_frame
            self.notify_lobby_server('players.busy',self.app.username)

    def join_server(self,serv_name,username):
        self.propose_name(serv_name,username)

    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.debug("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.debug("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

    def notify_lobby_server(self,key,message,props=None):
        self.notify_exchange(self.lobby_server,key,message,props)

    def propose_name(self,serv_name,username):
        self.notify_exchange(serv_name,'players.req',username,self.lobby_reply_prop)

    def request_playerlist(self):
        self.notify_lobby_server('players.ping','')

    def request_room(self,name):
        replyprop = pika.BasicProperties(reply_to=self.lobby_queue)
        self.notify_lobby_server('gameroom.add',name,replyprop)

    def join_room(self,name):
        replyprop = pika.BasicProperties(reply_to=self.lobby_queue)
        self.notify_lobby_server('gameroom.join',name,replyprop)

    def request_roomlist(self):
        self.notify_lobby_server('gameroom.ping','')

    def get_game_players(self):
        self.notify_exchange(self.room_name,"game.ping",'')

    def leave_server(self):
        self.notify_lobby_server('players.remove',self.app.username)
        self.connect_exchange(self.lobby_server,LOBBY_KEYS,self.lobby_queue,False)
        self.lobby_server = None

    def leave_game(self):
        self.game_ui = None
        self.connect_exchange(self.room_name,GAME_KEYS,self.game_queue,False)
        self.notify_exchange(self.room_name,"game.sayonara",self.app.username)
        self.notify_exchange(self.lobby_server,"players.available",self.app.username)
        self.room_name = ""

    def request_uri(self):
        self.notify_exchange(self.room_name,"game.requri",'')

    def disconnect(self):
        if self.app.username and self.lobby_server:
            self.notify_lobby_server('players.remove',self.app.username)
        if self.app.username and self.room_name:
            self.notify_exchange(self.room_name,"game.sayonara",self.app.username)
        self.channel.queue_delete(queue=self.server_queue)
        self.connection.close()

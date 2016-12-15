#!/usr/bin/env python
from utils import make_logger, SERV_EXCHANGE, DELIM
from threading import Thread
from keepalive import KeepAliveSpammer

import pika

LOBBY_KEYS = ["players.add", "players.remove","gameroom.add","gameroom.remove",\
    "players.busy","players.available","players.ping","gameroom.busy",\
    "gameroom.available"]
SERVER_KEYS = ["open","closed"]
Log = make_logger()
GAME_KEYS = ["game.next","game.leader","game.joined","game.sayonara","game.uri",\
"game.ping","game.start","game.fire","game.all_sunk","game.over","game.restart",\
"game.ready","game.configure","game.disconnected","game.skip","game.rejoined"]
#TODO: Field for ":" and other magic strings

"""
The class which handles all the connections for a single client
"""
class ClientConnector(Thread):
    """
    The constructor
    @param pikahost - the rabbitmq server
    @param client - the client application frame
    """
    def __init__(self,pikahost,client):
        Thread.__init__(self)
        self.app = client
        self.lobby_server = ""
        self.connect(pikahost)
        self.game_ui = None
        self.room_name = ""
        self.kas = None

    """
    Connecting the client to the rabbitmq server, declaring the exchanges,
    setting up callbacks
    @param pikahost the IP of the server
    """
    def connect(self,pikahost):
        #connect to broker
        credentials = pika.PlainCredentials('DSHW2', 'DSHW2')
        parameters = pika.ConnectionParameters(pikahost,5672,'/',credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        #connect to server declaration exchange
        self.make_queues()
        self.channel.exchange_declare(exchange=SERV_EXCHANGE,type='direct')
        self.connect_exchange(SERV_EXCHANGE,SERVER_KEYS,self.server_queue,True)

        self.channel.basic_consume(self.server_callback,
                              queue=self.server_queue,
                              no_ack=True)
        #self.channel.basic_qos(prefetch_count=1)


    """
    Just sets up all the sorts of queues we use
    server_queue -> information about joining/leaving servers
    lobby_queue -> information about people in servers, games popping up etc
    game_queue -> all game-related info
    """
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

    """
    just a convenience function which sends a message to an exchange
    """
    def ping_servers(self):
        self.notify_exchange(SERV_EXCHANGE,'ping_open','',self.lobby_reply_prop)

    """
    the run method of the thread. all it does is consume
    """
    def run(self):
        self.channel.start_consuming()

    """
    the callback method which handles server join/leave events and when
    the player can join a specific server
    """
    def server_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Server queue received message %r with key %r." % (body,rk))
        if rk == 'open':
            self.app.update_server_box(body,True)
        elif rk == 'closed':
            self.app.update_server_box(body,False)
        elif body.startswith("players.reject"):
            msg = body.split(DELIM,2)
            server = msg[1]
            name = msg[2]
            self.app.notify_rejection(server,name)
        elif body.startswith("players.confirm"):
            msg = body.split(DELIM,2)
            server_name = msg[1]
            self.lobby_server = server_name
            self.connect_exchange(server_name,LOBBY_KEYS,self.lobby_queue,True)
            self.app.username = msg[2]
            self.create_keepalive(server_name,self.app.username)
            self.app.hide_server_selection()
            self.app.show_lobby()

    """
    A function which creates the spammer that notifies the server that the
    player has not disconnected.
    @param server - the server to be notified of our existence
    @param username - our username to be sent as the message
    """
    def create_keepalive(self,server,username):
        self.kas = KeepAliveSpammer(self.channel,server,username)
        self.kas.setDaemon(True)
        self.kas.start()

    """
    A function which (dis)connects certain keys in an exchange to a queue. The
    wildcards of pika did not work for me, so I had to resort to this.
    @param server_name the exchange to bind from
    @keys the routing keys that we are interested in
    @q the queue to bind to
    @connect a flag whether to connect or disconnect
    """
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

    """
    The game callback, which handles all the game logic messages.
    """
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
        elif rk == "game.start":
            self.game_ui.start_game()
        elif rk == "game.fire":
            self.game_ui.fire(body)
        elif rk == "game.all_sunk":
            self.game_ui.gamebox.rcv_all_sunk(body)
        elif rk == "game.over":
            self.game_ui.gamebox.rcv_game_over(body)
        elif rk == "game.restart":
            self.game_ui.gamebox.rcv_restart_game()
        elif rk == "game.leader":
            self.game_ui.promote_to_leader(body)
        elif rk == "game.configure":
            self.game_ui.gamebox.rcv_game_configure()
        elif rk == "game.ready":
            self.game_ui.update_playercolour(body,'light sky blue')
        elif rk == "game.disconnected":
            self.game_ui.colour_name_red(body)
        elif rk == "game.skip":
            self.game_ui.skip()
        elif rk == "game.rejoined" and body == self.app.username:
            self.game_ui.rejoin()

    """
    The lobby callback which handles messages about players/rooms leaving or
    being busy/available
    """
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
        elif rk == 'gameroom.busy':
            self.app.mark_red(self.app.lobby_roomlist,body,True)
        elif rk == 'gameroom.available':
            self.app.mark_red(self.app.lobby_roomlist,body,False)
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
        elif body.startswith("gameroom.reject"):
            msg = body.split(DELIM)
            room = msg[1]
            self.app.notify_closed(room)

    """
    A wrapper for a slightly more apt name
    """
    def join_server(self,serv_name,username):
        self.propose_name(serv_name,username)

    """
    A function which just wraps the API function in itself, but also always logs
    """
    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.info("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.info("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

    """
    just a convenience function so you don't have to specify so many parameters
    and you have more of an idea what it is doing based on the function name
    """
    def notify_lobby_server(self,key,message,props=None):
        self.notify_exchange(self.lobby_server,key,message,props)

    """
    just a convenience function which sends a message to an exchange
    """
    def propose_name(self,serv_name,username):
        self.notify_exchange(serv_name,'players.req',username,self.lobby_reply_prop)

    """
    just a convenience function which sends a message to an exchange
    """
    def request_playerlist(self):
        self.notify_lobby_server('players.ping','')

    """
    just a convenience function which sends a message to an exchange
    also sets up some properties
    """
    def request_room(self, name, size):
        replyprop = pika.BasicProperties(reply_to=self.lobby_queue)
        self.notify_lobby_server('gameroom.request',name + DELIM + str(size),replyprop)

    """
    just a convenience function which sends a message to an exchange
    also sets up some properties
    """
    def join_room(self,name):
        replyprop = pika.BasicProperties(reply_to=self.lobby_queue)
        self.notify_lobby_server('gameroom.join',name+DELIM+self.app.username,replyprop)

    """
    just a convenience function which sends a message to an exchange
    """
    def request_roomlist(self):
        self.notify_lobby_server('gameroom.ping','')

    """
    just a convenience function which sends a message to an exchange
    """
    def get_game_players(self):
        self.notify_exchange(self.room_name,"game.ping",'')

    """
    Unsubscribes the server from the proper queue, stops the keep alive spammer,
    notifies server of leaving
    """
    def leave_server(self):
        self.notify_lobby_server('players.remove',self.app.username)
        self.connect_exchange(self.lobby_server,LOBBY_KEYS,self.lobby_queue,False)
        self.lobby_server = None
        self.kas.stop()
        self.kas = None

    """
    Notifies room of leaving and unsubscribes keys from exchange
    """
    def leave_game(self):
        self.game_ui = None
        self.connect_exchange(self.room_name,GAME_KEYS,self.game_queue,False)
        self.notify_exchange(self.room_name,"game.sayonara",self.app.username)
        self.notify_exchange(self.lobby_server,"players.available",self.app.username)
        self.room_name = ""


    """
    just a convenience function which sends a message to an exchange
    """
    def request_uri(self):
        self.notify_exchange(self.room_name,"game.requri",'')

    """
    Notifies people of us leaving and closes down any connections
    """
    def disconnect(self):
        if self.app.username and self.lobby_server:
            self.notify_lobby_server('players.remove',self.app.username)
        if self.app.username and self.room_name:
            self.notify_exchange(self.room_name,"game.sayonara",self.app.username)
        if self.kas:
            self.kas.stop()
        self.channel.queue_delete(queue=self.server_queue)
        self.connection.close()

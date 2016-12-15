import pika
from utils import make_logger, DELIM
from threading import Thread, Timer

Log = make_logger()
GAME_KEYS = ["game.next","game.leader","game.joined","game.sayonara",\
"game.requri","game.start","game.restart","game.kick"]
LOBBY_KEYS = ["players.disconnected"]
SHUTDOWN = 'gameroom.remove'

"""
A class which handles the callbacks of a certain game.
"""
class Gameroom(Thread):
    """
    The constructor
    @param pikahost - the rabbitmq server
    @param title - the name of the room
    @param serv - the host server
    @gameobject - the gameobject of the game, which handles all game logic
    @object_uri - the pyro4 uri of the gameobject
    """
    def __init__(self,pikahost,title,serv,gameobject,object_uri):
        Thread.__init__(self)
        self.open = True
        self.players = []
        self.disconnected_players = []
        self.owner = ""
        self.server = serv
        self.servname = self.server.servname
        self.roomname = title
        self.exchange = self.servname+DELIM+title
        self.uri = object_uri
        self.gamestate = gameobject
        Log.debug("Room %r online." % self.exchange)
        self.connect(pikahost)

    """
    Initializing the connection
    @param pikahost - the rabbitmq server
    """
    def connect(self,pikahost):
        credentials = pika.PlainCredentials('DSHW2', 'DSHW2')
        parameters = pika.ConnectionParameters(pikahost,5672,'/',credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.declare_exchanges()
        self.make_queue()
        self.bind_queue()

    """
    Declaring exchanges that the game needs
    """
    def declare_exchanges(self):
        self.channel.exchange_declare(exchange=self.servname)
        self.channel.exchange_declare(exchange=self.exchange)

    """
    Initializing queues
    """
    def make_queue(self):
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.game_queue = self.dec_result.method.queue

    """
    binding the necessary queues from the exchanges
    The LOBBY_KEYS one is required to detect when a person has disconnected
    from this game
    """
    def bind_queue(self):
        for key in GAME_KEYS:
            self.channel.queue_bind(exchange=self.exchange,
                                    queue=self.game_queue,
                                    routing_key=key)
        for key in LOBBY_KEYS:
            self.channel.queue_bind(exchange=self.servname,
                                    queue=self.game_queue,
                                    routing_key=key)
        self.channel.basic_consume(self.game_callback,queue=self.game_queue)


    """
    The main callback method of the game. Handles all game logic related stuff
    """
    def game_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.info("Game queue received message %r with key %r" % (body,rk))
        if rk == "game.joined":
            if body not in self.players:
                self.players.append(body)
            if not self.owner:
                self.owner = body
                self.notify_players("game.leader",self.owner)
            if body in self.gamestate.disconnected_players:
                self.gamestate.revive_player(body)
                self.notify_players("game.rejoined",body)
        elif rk == "game.sayonara":
            if body in self.players:
                self.players.remove(body)
            if not self.players:
                Log.debug("Nuking room %r", self.roomname)
                self.server.destroy_room(self.roomname)
            elif self.owner == body:
                self.owner = self.players[0]
                self.notify_players("game.leader",self.owner)
        elif rk == "game.requri":
            self.notify_players("game.uri",str(self.uri))
        elif rk == "game.start":
            self.open = False
            self.notify_exchange(self.servname,'gameroom.busy',self.roomname)
        elif rk == "game.restart":
            self.open = True
            self.notify_exchange(self.servname,'gameroom.available',self.roomname)
        elif rk == "players.disconnected":
            if body in self.players:
                Log.debug("Room %r had player %r disconnect." % (self.roomname,body))
                if self.gamestate.get_turn() == body:
                    Log.debug("It was that player's turn. Skipping..")
                    self.gamestate.switch_turn()
                    self.notify_players('game.skip','')
                self.gamestate.dc_player(body)
                self.notify_players('game.disconnected',body)
                if body == self.owner:
                    if len(self.players) == 1:
                        self.notify_players('game.sayonara',body)
                    else:
                        self.owner = self.players[1]
                        self.notify_players("game.leader",self.owner)
        elif rk == 'game.kick':
            if body in self.gamestate.disconnected_players:
                self.notify_players('game.sayonara',body)

    """
    A convenience method/wrapper for logging all messages.
    """
    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.info("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.info("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

    """
    A true convenience method since most communication is in this one exchange
    """
    def notify_players(self,key,message,props=None):
        self.notify_exchange(self.exchange,key,message,props)

    """
    The main method of the thread - it just consumes
    """
    def run(self):
        self.channel.start_consuming()

    """
    A method that notifies the server of its disappearence and shuts down the
    channel
    """
    def disconnect(self):
        self.notify_exchange(self.servname,SHUTDOWN,self.roomname)
        self.channel.close()

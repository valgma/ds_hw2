import pika
from utils import make_logger, DELIM
from threading import Thread, Timer

Log = make_logger()
GAME_KEYS = ["game.next","game.leader","game.joined","game.sayonara","game.requri"]
SHUTDOWN = 'gameroom.remove'

class Gameroom(Thread):
    def __init__(self,pikahost,title,serv,gameobject,object_uri):
        Thread.__init__(self)
        self.open = True
        self.players = []
        self.owner = ""
        self.server = serv
        self.servname = self.server.servname
        self.roomname = title
        self.exchange = self.servname+DELIM+title
        self.uri = object_uri
        Log.debug("Room %r online." % self.exchange)
        self.connect(pikahost)

    def connect(self,pikahost):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=pikahost))
        self.channel = self.connection.channel()
        self.declare_exchanges()
        self.make_queue()
        self.bind_queue()

    def declare_exchanges(self):
        self.channel.exchange_declare(exchange=self.servname)
        self.channel.exchange_declare(exchange=self.exchange)

    def make_queue(self):
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.game_queue = self.dec_result.method.queue

    def bind_queue(self):
        for key in GAME_KEYS:
            self.channel.queue_bind(exchange=self.exchange,
                                    queue=self.game_queue,
                                    routing_key=key)
        self.channel.basic_consume(self.game_callback,queue=self.game_queue)

    def game_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Game queue received message %r with key %r" % (body,rk))
        if rk == "game.joined":
            if body not in self.players:
                self.players.append(body)
            if not self.owner:
                self.owner = body
                self.notify_players("game.leader",self.owner)
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

    def notify_exchange(self,ex,key,message,props=None):
        if props:
            Log.debug("Sending exchange %r message %r with key %r with some extra properties." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message,properties=props)
        else:
            Log.debug("Sending exchange %r message %r with key %r." % (ex,message,key))
            self.channel.basic_publish(exchange=ex,routing_key=key,body=message)

    def notify_players(self,key,message,props=None):
        self.notify_exchange(self.exchange,key,message,props)

    def run(self):
        self.channel.start_consuming()

    def disconnect(self):
        self.notify_exchange(self.servname,SHUTDOWN,self.roomname)
        self.channel.close()

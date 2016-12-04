#!/usr/bin/env python
from utils import make_logger, SERV_EXCHANGE
from threading import Thread

import pika

GAME_KEYS = ["players.add"]
Log = make_logger()
#TODO: Field for ":" and other magic strings

class ClientConnector(Thread):
    def __init__(self,pikahost,client):
        Thread.__init__(self)
        self.connect(pikahost)
        self.ping_servers()
        self.app = client
        self.game_server = ""

    def connect(self,pikahost):
        #connect to broker
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=pikahost))
        self.channel = self.connection.channel()

        #connect to server declaration exchange
        self.channel.exchange_declare(exchange=SERV_EXCHANGE,
                                 type='direct')

        #create own message queue
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.lobby_queue = self.dec_result.method.queue

        self.game_dec = self.channel.queue_declare(exclusive=False)
        self.game_queue = self.game_dec.method.queue

        #listen to new declarations of open servers and closing servers
        self.channel.queue_bind(exchange=SERV_EXCHANGE,
                           queue=self.lobby_queue,
                           routing_key='open')
        self.channel.queue_bind(exchange=SERV_EXCHANGE,
                              queue=self.lobby_queue,
                              routing_key='closed')
        self.channel.basic_consume(self.callback,
                              queue=self.lobby_queue,
                              no_ack=True)
        #self.channel.basic_qos(prefetch_count=1)


    def ping_servers(self):
        self.channel.basic_publish(exchange=SERV_EXCHANGE,
                                  routing_key='ping_open',
                                  properties=pika.BasicProperties(
                                    reply_to = self.lobby_queue,
                                    ),
                                  body='')

    def run(self):
        self.channel.start_consuming()

    def callback(self, ch, method, properties, body):
        rk = method.routing_key
        if rk == 'open':
            self.app.update_server_box(body,True)
            print "[x] server %r is open" % body
        elif rk == 'closed':
            Log.debug("server %r has closed" % body)
            self.app.update_server_box(body,False)
        elif rk == 'player.confirmation':
            serv_name = body
            self.channel.queue_unbind(exchange=SERV_EXCHANGE,
                                      queue=self.lobby_queue,
                                      routing_key='#')
            self.channel.queue_bind(exchange=serv_name,
                                    queue=self.lobby_queue,
                                    routing_key='#')
        elif body.startswith("players.add"):
            msg = body.split(":",2)
            server_name = msg[1]
            for key in GAME_KEYS:
                self.channel.queue_bind(exchange=server_name,
                                        queue=self.game_queue,
                                        routing_key=key)
            self.channel.basic_consume(self.game_callback,
                                    queue=self.game_queue)
            self.game_server = server_name
            self.app.username = msg[2]
            self.app.show_lobby()
        else:
            print "Got junk %r" % body

    def game_callback(self, ch, method, properties, body):
        rk = method.routing_key
        if rk == 'players.add':
            self.app.update_client_box(body,True)

    def join_server(self,serv_name,username):
        self.propose_name(serv_name,username)


    def propose_name(self,serv_name,username):
        self.channel.exchange_declare(exchange=serv_name,
                                        type='direct')
        self.channel.basic_publish(exchange=serv_name,
                                   routing_key='players.req',
                                   body=username,
                                   properties=pika.BasicProperties(
                                     reply_to = self.lobby_queue)
                                     )
    def request_playerlist(self):
        self.channel.basic_publish(exchange=self.game_server,
                                    routing_key='players.ping',
                                    body='')


    def disconnect(self):
        self.channel.queue_delete(queue=self.lobby_queue)
        self.connection.close()

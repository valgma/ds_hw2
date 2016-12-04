#!/usr/bin/env python
#from utils import make_logger
import pika
import sys
from threading import Thread
from utils import make_logger, SERV_EXCHANGE

Log = make_logger()


class Server(Thread):
    def __init__(self,pikahost,title,own_name,master):
        Thread.__init__(self)
        self.servname = title
        self.connect(pikahost)
        self.app = master
        self.approved_clients = [own_name]



    def connect(self,pikahost):
        #connect to broker
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=pikahost))
        self.channel = self.connection.channel()

        #connect to server declaration exchange
        self.channel.exchange_declare(exchange=SERV_EXCHANGE,
                                        type='direct')

        #create server exchange
        self.channel.exchange_declare(exchange=self.servname,
                                     type='direct')

        #create lobby queue
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.lobby_queue = self.dec_result.method.queue

        #create game queue
        self.game_dec = self.channel.queue_declare(exclusive=True)
        self.game_queue = self.game_dec.method.queue

        #listen to clients asking for server list
        lobby_keys = ["ping_open"]
        for k in lobby_keys:
            self.channel.queue_bind(exchange=SERV_EXCHANGE,
                                    queue=self.lobby_queue,
                                    routing_key=k)

        #listen to own server exchange
        game_keys = ["players.req","players.ping"]
        for k in game_keys:
            self.channel.queue_bind(exchange=self.servname,
                                    queue=self.game_queue,
                                    routing_key=k)

        #Process requests
        self.channel.basic_consume(self.lobby_queue_callback,
                      queue=self.lobby_queue,
                      no_ack=True)

        self.channel.basic_consume(self.game_queue_callback,
                        queue=self.game_queue)

        #publish own channel in servers
        print "publishing channel"
        self.channel.basic_publish(exchange=SERV_EXCHANGE,
                                  routing_key='open',
                                  properties=pika.BasicProperties(
                                    reply_to = self.lobby_queue,
                                    ),
                                  body=self.servname)


    def self_publish_open(self,available):
        tag = 'open' if available else 'closed'
        self.channel.basic_publish(exchange=SERV_EXCHANGE,
                                  routing_key=tag,
                                  properties=pika.BasicProperties(
                                    reply_to = self.lobby_queue,
                                    ),
                                  body=self.servname)

    def run(self):
        self.channel.start_consuming()


    def disconnect(self):
        self.channel.exchange_delete(self.servname)
        self.self_publish_open(False)
        self.channel.close()

    def game_queue_callback(self, ch, method, properties, body):
        rk = method.routing_key
        Log.debug("Received game message %r with key %r" % (body,rk))
        if rk == 'players.req':
            if body not in self.approved_clients:
                self.approved_clients.append(body)
                target_queue = properties.reply_to
                self.notify_new_player(body,target_queue)
                self.app.update_client_box(body,True)
        if rk == 'players.ping':
            for player in self.approved_clients:
                self.channel.basic_publish(exchange=self.servname,
                                            routing_key='players.add',
                                            body=player)

    def notify_new_player(self,player_name,target):
       self.channel.basic_publish(exchange=self.servname,
                                  routing_key='players.add',
                                  body=player_name)

       self.channel.basic_publish(exchange='',
                                    routing_key=target,
                                    body="players.add:"+self.servname+":"+player_name)

    def lobby_queue_callback(self, ch, method, properties, body):
        rk = method.routing_key
        if rk == 'ping_open':
            print "received request for ID"
            self.self_publish_open(True)
        elif rk == 'players.req':
            print " [x] Received name request %r" % body
        else:
            print(" [x] Received %r" % body)

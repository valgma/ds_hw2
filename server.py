#!/usr/bin/env python
#from utils import make_logger
import pika
import sys
from threading import Thread
#Logg = make_logger()

SERV_EXCHANGE = 'servers2'


class Server(Thread):
    def __init__(self,pikahost,title):
        Thread.__init__(self)
        self.servname = title
        self.connect(pikahost)


    def connect(self,pikahost):
        #connect to broker
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=pikahost))
        self.channel = self.connection.channel()

        #connect to server declaration exchange
        self.channel.exchange_declare(exchange=SERV_EXCHANGE,
                         type='direct')

        #create game channel
        self.dec_result = self.channel.queue_declare(exclusive=True)
        self.own_queue = self.dec_result.method.queue

        #listen to requests of people saying hi
        self.channel.queue_bind(exchange=SERV_EXCHANGE,
                                queue=self.own_queue,
                                routing_key='hello')

        self.channel.queue_bind(exchange=SERV_EXCHANGE,
                                queue=self.own_queue,
                                routing_key='ping_open')


        #Process requests
        self.channel.basic_consume(self.callback,
                      queue=self.own_queue,
                      no_ack=True)

        #publish own channel in servers
        print "publishing channel"
        self.channel.basic_publish(exchange=SERV_EXCHANGE,
                                  routing_key='open',
                                  properties=pika.BasicProperties(
                                    reply_to = self.own_queue,
                                    ),
                                  body=self.servname)


    def self_publish_open(self,available):
        tag = 'open' if available else 'closed'
        self.channel.basic_publish(exchange=SERV_EXCHANGE,
                                  routing_key=tag,
                                  properties=pika.BasicProperties(
                                    reply_to = self.own_queue,
                                    ),
                                  body=self.servname)

    def run(self):
        self.channel.start_consuming()


    def disconnect(self):
        self.self_publish_open(False)
        self.channel.close()

    def callback(self, ch, method, properties, body):
        rk = method.routing_key
        if rk == 'ping_open':
            print "received request for ID"
            self.self_publish_open(True)
        else:
            print(" [x] Received %r" % body)

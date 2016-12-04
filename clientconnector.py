#!/usr/bin/env python
from utils import make_logger
from threading import Thread

import pika

SERV_EXCHANGE = 'servers2'
Log = make_logger()

class ClientConnector(Thread):
    def __init__(self,pikahost,client):
        Thread.__init__(self)
        self.connect(pikahost)
        self.ping_servers()
        self.clientApp = client
        self.server_addresses = {}

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
        self.queue_name = self.dec_result.method.queue

        #listen to new declarations of open servers and closing servers
        self.channel.queue_bind(exchange=SERV_EXCHANGE,
                           queue=self.queue_name,
                           routing_key='open')
        self.channel.queue_bind(exchange=SERV_EXCHANGE,
                              queue=self.queue_name,
                              routing_key='closed')
        self.channel.basic_consume(self.callback,
                              queue=self.queue_name,
                              no_ack=True)


    def ping_servers(self):
        self.channel.basic_publish(exchange=SERV_EXCHANGE,
                                  routing_key='ping_open',
                                  properties=pika.BasicProperties(
                                    reply_to = self.queue_name,
                                    ),
                                  body='')

    def run(self):
        self.channel.start_consuming()

    def callback(self, ch, method, properties, body):
        rk = method.routing_key
        if rk == 'open':
            self.clientApp.update_server_box(body,True)
            self.server_addresses[body] = properties.reply_to
            print "[x] server %r is open" % body
            print self.server_addresses
        elif rk == 'closed':
            Log.debug("server %r has closed" % body)
            self.clientApp.update_server_box(body,False)
            del self.server_addresses[body]

    def join_server(self,serv_name,username):
        replyQueue = self.server_addresses[serv_name]
        self.channel.basic_publish(exchange='',
                                   routing_key=replyQueue,
                                   body=username)

    def disconnect(self):
        self.connection.close()

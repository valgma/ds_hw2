#!/usr/bin/env python
from utils import make_logger
import pika

SERV_EXCHANGE = 'servers2'
Log = make_logger()

class Client:
    def __init__(self,pikahost):
        self.connect(pikahost)
        self.ping_servers()
        self.run()

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
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.close()

    def callback(self, ch, method, properties, body):
        rk = method.routing_key
        if rk == 'open':
            print "[x] server %r is open" % body
        elif rk == 'closed':
            Log.debug("server %r has closed" % body)

c = Client('localhost')

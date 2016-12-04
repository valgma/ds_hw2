import logging
def make_logger():
    FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
    logging.basicConfig(level=logging.DEBUG,format=FORMAT)
    LOG = logging.getLogger()
    logging.getLogger("pika").propagate = False
    return LOG

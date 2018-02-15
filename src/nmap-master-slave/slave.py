import time
import zmq
import random
import sys
import argparse
from logbook import StreamHandler, FileHandler, Logger
from custom_exceptions import SocketNotConnected
from seeker import scan_port
from consts import SLAVE_ERROR_SIGNAL, SLAVE_LOG_FILE, SLAVE_OK_SIGNAL, REPORT_PORT, ZMQ_PROTOCOL, MASTER_IP

# StreamHandler(sys.stdout, bubble=True, level='DEBUG').push_application()
FileHandler(SLAVE_LOG_FILE, bubble=True, level='INFO').push_application()
logger = Logger('Master')
context = zmq.Context()


def callback(host, result):
    print(host, result)


class Slave(object):
    """
    A slave that will listen on one port for jobs and execute them while reporting back to the master.
    """

    def __init__(self, id, port):
        self.id = id
        self.port = port
        self._receive_socket = None
        self._report_socket = None

    @staticmethod
    def _check_socket(socket):
        """
        Checks if the given socket was connected via the connect method.
        Raises and exception if it isn't
        :param zmq.sugar.socket.Socket socket:
        :return zmq.sugar.socket.Socket: The socket if it was connected
        """
        if socket is None:
            raise SocketNotConnected()
        else:
            return socket

    @property
    def receive_socket(self):
        return self._check_socket(self._receive_socket)

    @property
    def report_socket(self):
        return self._check_socket(self._report_socket)

    def connect(self):
        """
        Connects all of the sockets to their ports.
        """
        self._receive_socket = context.socket(zmq.PULL)
        self._report_socket = context.socket(zmq.PUSH)
        self._receive_socket.connect(
            "{protocol}://{ip}:{port}".format(protocol=ZMQ_PROTOCOL, ip=MASTER_IP, port=self.port))
        self._report_socket.connect(
            "{protocol}://{ip}:{port}".format(protocol=ZMQ_PROTOCOL, ip=MASTER_IP, port=REPORT_PORT))

    def start(self):
        """
        Starts the slave.
        The slave will listen via the receive socket until a job was sent, execute the job and then report back to the
        master.
        """
        while True:
            data = self.receive_socket.recv_json()
            logger.info('working on {}'.format(data['ip']))
            try:
                scan_port(callback=callback, **data)
            except ValueError:
                self.report_socket.send_json({'status': SLAVE_ERROR_SIGNAL})
                logger.exception()
            else:
                self.report_socket.send_json({'status': SLAVE_OK_SIGNAL})


def start_slave(port=5555):
    slave_id = random.randrange(1, 10005)
    slave = Slave(slave_id, port)
    slave.connect()
    slave.start()


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest='port', type=int, help='The port on which the slave will run')
    return parser.parse_args().port


if __name__ == '__main__':
    try:
        port = parse_arguments()
        start_slave(port=port)
    except (KeyboardInterrupt, SystemExit):
        # We want to be able to abort the running of the code without a strange log :)
        raise
    except Exception:
        logger.exception()
        raise

import zmq
import random
import sys
import argparse
from datetime import datetime as dt
from logbook import StreamHandler, FileHandler, Logger
from custom_exceptions import SocketNotConnected, ParseException
from seeker import scan_port
from consts import SLAVE_ERROR_SIGNAL, SLAVE_LOG_FILE_FORMAT, SLAVE_OK_SIGNAL, REPORT_PORT, ZMQ_PROTOCOL, MASTER_IP
from writer import MysqlWriter
from db import get_session
from orm import NmapScan

SLAVE_ID = random.randrange(1, 10005)
StreamHandler(sys.stdout, bubble=True, level='DEBUG').push_application()
FileHandler(SLAVE_LOG_FILE_FORMAT.format(id=SLAVE_ID), bubble=True, level='INFO').push_application()
logger = Logger('Master')
context = zmq.Context()


class Slave(object):
    """
    A slave that will listen on one port for jobs and execute them while reporting back to the master.
    """

    def __init__(self, id, port):
        self.id = id
        self.port = port
        self._receive_socket = None
        self._report_socket = None
        self.session = get_session()

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
            logger.info("Waiting for connection")
            data = self.receive_socket.recv_json()
            logger.info('working on {}'.format(data['ip']))
            writer = MysqlWriter(npm_scan_id=data['scan_id'], logger=logger, session=self.session)
            try:
                self._update_scan_status(data['scan_id'])
                scan_port(callback=writer.write_results_to_db, ip=data['ip'], **data['params'])
            except (ValueError, ParseException):
                self.report_socket.send_json({'status': SLAVE_ERROR_SIGNAL})
                logger.exception()
            else:
                self.report_socket.send_json({'status': SLAVE_OK_SIGNAL})

    def _update_scan_status(self, scan_id):
        scan = self.session.query(NmapScan).get(scan_id)
        scan.start_time = dt.now()
        scan.status = 'Running'
        self.session.commit()


def parse_arguments():
    """
    Retrieves the arguments from the command line.
    :return int: The port in which the slave will listen.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest='port', type=int, help='The port on which the slave will run')
    return parser.parse_args().port


if __name__ == '__main__':
    try:
        port = parse_arguments()
        slave = Slave(id=SLAVE_ID, port=port)
        slave.connect()
        slave.start()
    except (KeyboardInterrupt, SystemExit):
        # We want to be able to abort the running of the code without a strange log :)
        raise
    except Exception:
        logger.exception()
        raise

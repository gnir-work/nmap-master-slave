import zmq
import sys
from logbook import StreamHandler, Logger, FileHandler
from consts import MASTER_LOG_FILE, REPORT_PORT, MASTER_IP
from itertools import cycle

# StreamHandler(sys.stdout, bubble=True, level='DEBUG').push_application()
FileHandler(MASTER_LOG_FILE, bubble=True, level='INFO').push_application()
logger = Logger('Master')
context = zmq.Context()
SLAVE_PORTS = [5555, 5556]


def _retrieve_ips_to_scan():
    return ['127.0.0.1', '127.0.0.1', '127.0.0.1', '127.0.0.1', '127.0.0.1', '127.0.0.1']


def _create_slave_socket(port):
    slave_socket = context.socket(zmq.PUSH)
    slave_socket.bind('tcp://{ip}:{port}'.format(ip=MASTER_IP, port=port))
    return slave_socket


def start_master():
    slave_sockets_iter = cycle(map(_create_slave_socket, SLAVE_PORTS))
    ips_to_scan = _retrieve_ips_to_scan()
    # receive status
    reporter = context.socket(zmq.PULL)
    reporter.bind("tcp://{ip}:{port}".format(ip=MASTER_IP, port=REPORT_PORT))

    for index, ip in enumerate(ips_to_scan):
        print('sending', ip)
        next(slave_sockets_iter).send_json({'ip': ip, 'ports': '1-10', 'opt': 'sS'})

    for ip in ips_to_scan:
        print('done', ip, reporter.recv_json())


if __name__ == '__main__':
    try:
        start_master()
    except (KeyboardInterrupt, SystemExit):
        # We want to be able to abort the running of the code without a strange log :)
        raise
    except Exception:
        logger.exception()
        raise

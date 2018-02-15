import zmq
import sys
from logbook import StreamHandler, Logger, FileHandler
from consts import MASTER_LOG_FILE, REPORT_PORT, MASTER_IP
from itertools import cycle
from orm import NmapScan
from db import get_session

StreamHandler(sys.stdout, bubble=True, level='DEBUG').push_application()
FileHandler(MASTER_LOG_FILE, bubble=True, level='INFO').push_application()
logger = Logger('Master')
context = zmq.Context()
SLAVE_PORTS = [5555]
session = get_session()


def _retrieve_ips_to_scan():
    """
    Needs to be implemented
    :return:
    """
    return ['127.0.0.1']


def _create_slave_socket(port):
    """
    Creates and binds a socket to the given port
    :param int port: The port on to which the socket will bind
    :return zmq.sugar.socket.Socket: The configured socket
    """
    slave_socket = context.socket(zmq.PUSH)
    slave_socket.bind('tcp://{ip}:{port}'.format(ip=MASTER_IP, port=port))
    return slave_socket


def _send_ips_to_slaves(ips_to_scan, slave_sockets):
    """
    Distributes the scanning between the slaves in a cycle.
    :param list of str ips_to_scan:
    :param itertools.cycle slave_sockets:
    :return:
    """
    for index, ip in enumerate(ips_to_scan):
        logger.info('scanning {ip}...'.format(ip=ip))
        scan = _create_new_scan(ip)
        next(slave_sockets).send_json(
            {'ip': ip, 'scan_id': scan.id, 'configuration': {'ports': '3000-3010', 'opt': 'sS', 'params': ''}})


def _create_new_scan(ip):
    scan = NmapScan(ip=ip, status="In Queue")
    session.add(scan)
    session.commit()
    return scan


def _send_mail():
    """
    Needs to be implemeted
    :return:
    """
    logger.info("Sending notification mail...")


def start_master():
    ips_to_scan = _retrieve_ips_to_scan()
    slave_sockets_iter = cycle(map(_create_slave_socket, SLAVE_PORTS))

    # Create report socket
    reporter = context.socket(zmq.PULL)
    reporter.bind("tcp://{ip}:{port}".format(ip=MASTER_IP, port=REPORT_PORT))

    _send_ips_to_slaves(ips_to_scan, slave_sockets_iter)

    # Wait for all of the scans to complete or fail
    for ip in ips_to_scan:
        logger.info('Done scanning {ip} with status: {status}'.format(ip=ip, status=reporter.recv_json()['status']))


if __name__ == '__main__':
    try:
        start_master()
    except (KeyboardInterrupt, SystemExit):
        # We want to be able to abort the running of the code without a strange log :)
        raise
    except Exception:
        logger.exception()
        raise

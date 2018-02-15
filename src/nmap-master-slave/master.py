import zmq
import sys
from logbook import StreamHandler, Logger, FileHandler
from consts import MASTER_LOG_FILE, REPORT_PORT

StreamHandler(sys.stdout, bubble=True, level='DEBUG').push_application()
FileHandler(MASTER_LOG_FILE, bubble=True, level='INFO').push_application()
logger = Logger('Master')
context = zmq.Context()


def _retrieve_ips_to_scan():
    return range(20)


def start_master():
    # Slave socket
    slave_socket = context.socket(zmq.PUSH)
    slave_socket.bind('tcp://127.0.0.1:5555')
    ips_to_scan = _retrieve_ips_to_scan()
    # receive status
    reporter = context.socket(zmq.PULL)
    reporter.bind("tcp://127.0.0.1:{port}".format(port=REPORT_PORT))

    for ip in ips_to_scan:
        print('sending', ip)
        slave_socket.send_json({'ip': ip})

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

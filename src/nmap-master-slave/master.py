import zmq
import sys
from logbook import StreamHandler, Logger, FileHandler
from custom_exceptions import ReporterException
from consts import REPORTER_OK_SIGNAL, REPORTER_ADDRESS, MASTER_LOG_FILE

StreamHandler(sys.stdout, bubble=True, level='DEBUG').push_application()
FileHandler(MASTER_LOG_FILE, bubble=True, level='INFO').push_application()
logger = Logger('Reporter')
context = zmq.Context()


def _send_reporter_number_of_ips(reporter_socket, number_of_ips):
    """
    Try to send the number of ips that will be send to the reported and raise and exceptions upon failure.
    :param zmq.sugar.socket.Socket reporter_socket: The zmq socket that connects to the reporter process.
    :param int number_of_ips:
    :return bool: True on success
    """
    reporter_socket.send(str(number_of_ips))
    if reporter_socket.recv() == REPORTER_OK_SIGNAL:
        return True
    else:
        raise ReporterException("Failed to send the reporter the number of ips that will be scanned.\n"
                                "Please check both the masters and reporters logs.")


def start_master():
    # Report socket
    reporter_socket = context.socket(zmq.REQ)
    reporter_socket.connect(REPORTER_ADDRESS)
    _send_reporter_number_of_ips(reporter_socket, 29)


if __name__ == '__main__':
    try:
        start_master()
    except (KeyboardInterrupt, SystemExit):
        # We want to be able to abort the running of the code without a strange log :)
        raise
    except Exception:
        logger.exception()
        raise

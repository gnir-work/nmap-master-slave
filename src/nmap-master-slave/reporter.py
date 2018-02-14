import zmq
from logbook import Logger, FileHandler, StreamHandler
import sys
from consts import REPORTER_ERROR_SIGNAL, REPORTER_OK_SIGNAL, REPORTER_ADDRESS, REPORTER_LOG_FILE

StreamHandler(sys.stdout, bubble=True, level='DEBUG').push_application()
FileHandler(REPORTER_LOG_FILE, bubble=True, level='INFO').push_application()
logger = Logger('Reporter')
context = zmq.Context()


def _retrieve_number_of_ip_that_will_be_scanned(master_socket):
    """
    Retrieves the number of ips that will be scanned from the master process.
    This is necessary in order for the reporter to know when it is time to report.
    :param zmq.sugar.socket.Socket master_socket: The socket through which the reported will speak with the client
    :return: The number of ips that will be scanned.
    """
    try:
        number_of_ips = int(master_socket.recv())
        if number_of_ips:
            logger.info("Waiting for status on {} scans...".format(number_of_ips))
            master_socket.send(REPORTER_OK_SIGNAL)
            return number_of_ips
        else:
            print "number of ips that will be scanned cannot be zero!"
            master_socket.send(REPORTER_ERROR_SIGNAL)
    except Exception:
        print "Failed in retrieving number of ips that will be processed. Aborting!"
        # socket.send(REPORTER_ERROR_SIGNAL)
        raise


def start_reporter():
    master_socket = context.socket(zmq.REP)
    master_socket.bind(REPORTER_ADDRESS)
    number_of_ips = _retrieve_number_of_ip_that_will_be_scanned(master_socket)
    for _ in xrange(number_of_ips):
        # Will be implemented
        pass


if __name__ == '__main__':
    try:
        start_reporter()
    except (KeyboardInterrupt, SystemExit):
        # We want to be able to abort the running of the code without a strange log :)
        raise
    except Exception:
        logger.exception()
        raise

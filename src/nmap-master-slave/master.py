import zmq
import smtplib
import sys
from logbook import StreamHandler, Logger, FileHandler
from consts import MASTER_LOG_FILE, REPORT_PORT, MASTER_IP, RECEIVER_MAIL, SENDER_MAIL, SENDER_PASSWORD, SMTP_CONFIG
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


def _parse_flags(flags):
    """
    Parse the falgs that are passed to the script.
    This logic is taken from the main of seeker.py however the python code was altered a little bit (with no change
    to the logic)
    :param str flags: All of the flags that were passed to the script.
    :return tuple: (list of nmap arguments, additional arguments that will be passed to nmap on top of the default ones)
    """
    nmap_args = []
    additional_params = ''
    # Check if -Pn option is needed
    if 't' in flags:
        # Forced scan (skip discovery) on TCP Syn and UPD
        if 'v' in flags:
            if 't1' in flags:
                nmap_args.extend(['-sU -sV', '-sV', '-Pn -sU -sV', '-Pn -sV'])
            else:
                nmap_args.extend(['-sU -sV -Pn', '-sV -Pn'])
        else:
            if 't1' in flags:
                nmap_args.extend(['-sS', '-sU', '-Pn -sU', '-Pn -sV'])
            else:
                nmap_args.extend(['-Pn -sS', '-Pn -sU'])
    else:
        # Normal Scan
        if 'v' in flags:
            nmap_args.extend(['-sV', '-sU -A'])
        else:
            nmap_args.extend(['-sS', '-sU'])

    # Check Parameters------------------------------------
    # Protocol Scan. This triggers if option p is enabled
    if 'p' in flags:
        # Protocol Scanning
        nmap_args.append('-sO')

    # Include connect scan -sT
    if 'o' in flags:
        nmap_args.append('-sT')

    # Append Null and Fin on the scan
    nmap_args.extend(['-sN', '-sF'])

    # Include closed port
    if 'c' in flags:
        additional_params = ' -ddd'
    return nmap_args, additional_params


def _send_ips_to_slaves(ips_to_scan, slave_sockets, flags):
    """
    Distributes the scanning between the slaves in a cycle.
    :param list of str ips_to_scan:
    :param itertools.cycle slave_sockets:
    :return scan: The scan that was initialized
    """
    for index, ip in enumerate(ips_to_scan):
        logger.info('scanning {ip}...'.format(ip=ip))
        scan = _create_new_scan(ip)
        opt, additional_args = _parse_flags(flags)
        next(slave_sockets).send_json(
            {'ip': ip, 'scan_id': scan.id,
             'configuration': {'ports': '3000-3010', 'opt': opt, 'additional_args': additional_args, 'params': flags}})


def _create_new_scan(ip):
    """
    Create a new scan in db and return it
    :param str ip: The ip on which the scan will run
    """
    scan = NmapScan(ip=ip, status="In Queue")
    session.add(scan)
    session.commit()
    return scan


def _send_mail(ips):
    """
    Sends an email notifying that the scan was complete
    """
    logger.info("Sending notification mail...")
    to = RECEIVER_MAIL
    subject = 'A Scan has finished!'
    text = 'The scan of the following ips: {} has finished'.format(ips)

    server = smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'])
    server.ehlo()
    server.starttls()
    server.login(SENDER_MAIL, SENDER_PASSWORD)

    BODY = 'To: {}\r\nFROM: {}\r\nSUBJECT: {}\r\n\r\n{}'.format(to, SENDER_MAIL, subject, text)

    server.sendmail(SENDER_MAIL, [to], BODY)
    logger.info("Done sending email!")

    server.quit()


def start_master():
    ips_to_scan = _retrieve_ips_to_scan()
    slave_sockets_iter = cycle(map(_create_slave_socket, SLAVE_PORTS))

    # Create report socket
    reporter = context.socket(zmq.PULL)
    reporter.bind("tcp://{ip}:{port}".format(ip=MASTER_IP, port=REPORT_PORT))

    _send_ips_to_slaves(ips_to_scan, slave_sockets_iter, flags='cp')

    # Wait for all of the scans to complete or fail
    for ip in ips_to_scan:
        logger.info('Done scanning {ip} with status: {status}'.format(ip=ip, status=reporter.recv_json()['status']))

    _send_mail(ips_to_scan)


if __name__ == '__main__':
    try:
        start_master()
    except (KeyboardInterrupt, SystemExit):
        # We want to be able to abort the running of the code without a strange log :)
        raise
    except Exception:
        logger.exception()
        raise

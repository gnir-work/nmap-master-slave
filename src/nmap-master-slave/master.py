import argparse
from collections import namedtuple
import zmq
import smtplib
import sys
from logbook import StreamHandler, Logger, FileHandler
from consts import MASTER_LOG_FILE, REPORT_PORT, MASTER_IP, RECEIVER_MAIL, SENDER_MAIL, SENDER_PASSWORD, SMTP_CONFIG, \
    SLAVE_ERROR_SIGNAL
from itertools import cycle
from orm import NmapScan
from db import get_session
from netaddr import IPNetwork
from collections import defaultdict

StreamHandler(sys.stdout, bubble=True, level='DEBUG').push_application()
FileHandler(MASTER_LOG_FILE, bubble=True, level='INFO').push_application()
logger = Logger('Master')
context = zmq.Context()
SLAVE_PORTS = [5555, 5556]
session = get_session()
NmapParameters = namedtuple('NmapParameters', ('nmap_params', 'additional_params'))
queues = defaultdict(list)


def _divide_range_to_singe_ips(ip_range):
    """
    Divide a range of ips into a list of single ips.
    :param str ip_range: A range of ips for example 173.193.189.144/28
    :return:
    """
    return [str(single_ip) for single_ip in list(IPNetwork(ip_range))]


def _retrieve_ips_to_scan(source_file_name, divide_ips=False):
    """
    Retrieve a list of ips to scan.
    The function reads the list from a file.
    :param str source_file_name: The name of the file which contains the ips
    :param bool divide_ips: A flag which indicates whether an ip range should be divided to single ips
    :return list of str: A list of ips or ip ranges
    """
    with open(source_file_name) as ips_file:
        ip_ranges = [ip_range.strip() for ip_range in ips_file.readlines()]
        if divide_ips:
            return [ip
                    for ip_range in ip_ranges
                    for ip in _divide_range_to_singe_ips(ip_range)]
        return ip_ranges


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
    return NmapParameters(nmap_params=nmap_args, additional_params=additional_params)


def _send_ips_to_slaves(ips_to_scan, slave_ports, flags, nmap_params, ports):
    """
    Distributes the scanning between the slaves in a cycle and saves the queues in a dict for management.
    :param list of str ips_to_scan:
    :param str flags: The flags that were passed to the script
    :param NmapParameters nmap_params: A named tuple that conatins the main and additional params for the script.
    :param str ports: The ports to scan.
    :return list: The ips that failed
    """
    slave_sockets = cycle(map(_create_slave_socket, slave_ports))
    logger.info("Scanning {} ips".format(ips_to_scan))
    for index, ip in enumerate(ips_to_scan):
        current_slave_port = slave_ports[index % len(slave_ports)]
        logger.info('scanning {ip} on port {port}...'.format(ip=ip, port=current_slave_port))
        scan = _create_new_scan(ip)
        next(slave_sockets).send_json(
            {'ip': ip, 'scan_id': scan.id,
             'configuration': {'ports': ports, 'opt': nmap_params.nmap_params,
                               'additional_args': nmap_params.additional_params, 'params': flags}})
        queues[current_slave_port].append(ip)


def _wait_for_scans_to_complete(ips_to_scan, reporter):
    """
    Waits for the scan to complete.
    In case a scan has failed the function will update the managed queues dict.
    :param list ips_to_scan:
    :param zmq.sugar.socket.Socket reporter: The socket to which the slaves report.
    :return tuple: (list of ports of the dead slaves, list of ips that have failed)
    """
    failed_scans = []
    dead_slaves = []
    # Wait for all of the scans to complete or fail
    logger.info("The queues state: {}".format(queues))
    for ip in ips_to_scan:
        data = reporter.recv_json()
        logger.info('Done scanning {ip} with status: {status}'.format(ip=ip, status=data['status']))
        if data['status'] == SLAVE_ERROR_SIGNAL:
            logger.info("Adding {} to failed scans".format(queues[data['port']]))
            failed_scans.extend(queues[data['port']])
            dead_slaves.append(data['port'])
            for ip in queues[data['port']][1:]:
                logger.info("Not waiting for {} as the slave died".format(ip))
                ips_to_scan.remove(ip);
            del queues[data['port']]
        else:
            queues[data['port']].remove(ip)
    return dead_slaves, failed_scans


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

    body = 'To: {}\r\nFROM: {}\r\nSUBJECT: {}\r\n\r\n{}'.format(to, SENDER_MAIL, subject, text)

    server.sendmail(SENDER_MAIL, [to], body)
    logger.info("Done sending email!")

    server.quit()


def start_master(ips_to_scan, flags, ports):
    """
    Start the master.
    The master will try to send to ips to the slaves that are currently alive,
    The master will continue distributing the ips to slave until there are no ips or no slaves alive.
    :param ips_to_scan: The ips to scan
    :param flags: The flags that will be parsed to nmap scans
    :param ports: The ports that will be scanned
    """
    nmap_params = _parse_flags(flags)

    # Create report socket
    reporter = context.socket(zmq.PULL)
    reporter.bind("tcp://{ip}:{port}".format(ip=MASTER_IP, port=REPORT_PORT))

    slave_ports = SLAVE_PORTS
    ips_sent_for_scan = ips_to_scan

    while ips_to_scan:
        _send_ips_to_slaves(ips_to_scan, flags=flags, nmap_params=nmap_params, slave_ports=slave_ports, ports=ports)
        dead_slaves, failed_scans = _wait_for_scans_to_complete(ips_to_scan, reporter)
        logger.info("Scan cycle result:")
        logger.info("dead slaves: {}".format(dead_slaves))
        logger.info("failed scans: {}".format(failed_scans))

        slave_ports = list(set(slave_ports) - set(dead_slaves))
        logger.info("slave ports: {}".format(slave_ports))
        if slave_ports:
            ips_to_scan = failed_scans
        else:
            raise Exception("No more slaves left :(")

    #_send_mail(ips_sent_for_scan)


def parse_arguments():
    """
    Retrieves the arguments from the command line.
    :return int: The port in which the slave will listen.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", dest='ips_source_file_name', type=str,
                        help='The name of the file which will '
                             'contain the list of ips (can be relative or absolute path)', required=True)
    parser.add_argument("--divide", dest='divide_ips', action='store_true',
                        help='A flag which indicates whether an ips range should be a single job for one'
                             'slave or should the master divide the range to single ips and each ip will'
                             'be considered a job for a slave', default=False)
    parser.add_argument("--flags", dest='flags', type=str,
                        help='The flags of the script (see the README.md file)', required=True)

    parser.add_argument("-p", "--ports", dest='ports', type=str,
                        help='The ports which will be scanned for the ips.', required=True)

    return parser.parse_args()


if __name__ == '__main__':
    try:
        arguments = parse_arguments()
        ips_to_scan = _retrieve_ips_to_scan(arguments.ips_source_file_name, divide_ips=arguments.divide_ips)
        start_master(ips_to_scan=ips_to_scan, flags=arguments.flags, ports=arguments.ports)
    except (KeyboardInterrupt, SystemExit):
        # We want to be able to abort the running of the code without a strange log :)
        raise
    except Exception:
        logger.exception()
        raise

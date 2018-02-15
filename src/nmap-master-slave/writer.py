from custom_exceptions import ParseException
from orm import PortScan
from db import get_session, get_scan_by_id

PROTOCOLS = ['tcp', 'udp', 'gre', 'ip']


class MysqlWriter(object):
    def __init__(self, npm_scan_id, logger, ignore_closed_ports, session=None):
        self.npm_scan_id = npm_scan_id
        self.logger = logger
        self._session = session
        self.ignore_closed_ports = ignore_closed_ports
        self.logger.info(
            "Created new Writer with the following configuration: id: {}, ignore closed_ports: {}".format(npm_scan_id,
                                                                                                          ignore_closed_ports))

    @property
    def session(self):
        if self._session is None:
            self._session = get_session()
        return self._session

    def write_results_to_db(self, host, result):
        self._check_result(host, result)
        self.logger.info("Starting to parse scan from {}...".format(host))

        scan = get_scan_by_id(self.npm_scan_id, self.session)
        scan.elapsed = result['nmap']['scanstats']['elapsed']

        for protocol in filter(lambda prot: prot in PROTOCOLS, result['scan'][host]):
            for port in result['scan'][host][protocol]:
                try:
                    if not self.ignore_closed_ports or result['scan'][host][protocol][port]['reason'] in (
                            'no-response', 'reset'):
                        scanned_port = PortScan(port=port,
                                                protocol=protocol,
                                                state=result['scan'][host][protocol][port]['state'],
                                                name=result['scan'][host][protocol][port].get('name', ''),
                                                method=result['nmap']['scaninfo'][protocol]['method'],
                                                reason=result['scan'][host][protocol][port]['reason'],
                                                product=result['scan'][host][protocol][port]['product'],
                                                version=result['scan'][host][protocol][port]['version'])
                        scan.ports.append(scanned_port)
                except Exception:
                    # Make sure nothing strange happens in the db.
                    self.session.rollback()
                    raise
            self.logger.info("Found {} ports on {}".format(len(scan.ports), host))
            self.session.commit()

    @staticmethod
    def _check_result(host, result):
        if result is None:
            raise ParseException("Received empty scan on host: {}".format(host))
        if int(result['nmap']['scanstats']['uphosts']) == 0:
            raise ParseException("Host {} is down!".format(host))
        if int(result['nmap']['scanstats']['uphosts']) > 1:
            raise ParseException("Can't handle multiple hosts! (from scan on {})".format(host))

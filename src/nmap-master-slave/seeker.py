#!usr/bin/python
import sys
import threading
import os
import re
import datetime
from nmap import PortScannerAsync
from multiprocessing.dummy import Pool as ThreadPool


class NmapWaitForMe(PortScannerAsync):
    # I need to Polymorph PortScannerAsync in order for nmap to wait for other callback Process,
    # otherwise it will prematurely terminate
    def check_for_proc(self):
        if self._process.is_alive():
            self._process.join()


# FUNCTIONS ----------------------------------------------
# This function will parse the result dump the needed info on a file
def callback_result(host, result):
    print(host, result)


# Thread
# for port scanning
def scan_port(opt, ip=None, ports=None, params=None, port_add_arguments=None, callback=None):
    # Backwards compatibility
    if ip is None:
        ip = sys.argv[1]
    if ports is None:
        ports = sys.argv[2]
    if port_add_arguments is None:
        port_add_arguments = port_add_args
    if params is None and len(sys.argv) == 5:
        params = sys.argv[4]

    callback = callback or callback_result

    print('Initiating thread for %s' % opt)
    if opt == '-sO':
        scanner.scan(ip, arguments='-sO', callback=callback, sudo=True)
    else:
        if params and params.find('t1') != -1 and re.match(r'-Pn .*', opt):
            scanner.scan(ip, known_vpn_port, opt + port_add_arguments, callback=callback, sudo=True)
        else:
            scanner.scan(ip, ports, opt + port_add_arguments, callback=callback, sudo=True)
    scanner.check_for_proc()
    while scanner.still_scanning():
        try:
            scanner.wait(2)
        except(KeyboardInterrupt):
            scanner.stop()
            pool.terminate()
            os.system('killall -9 nmap')
            raise


# Display syntax
def display_usage():
    print('Syntax: seeker <ip> <port> <filename> <options:pc>\n')
    print('\tip - For multiple IPs, enclose it with \"\". ex.\"192.168.0.1\\24 192.168.10.0\\24\"\n')
    print('By default, this script will run -sS (syn), -sU (udp), -sN (null) and -sF (fin)\n')
    print('OPTIONS\n')
    print('Scanning:')
    print('\tp - Includes protocol scanning (-sO). (slow)')
    print('\to - Includes tcp connect scan (-sT).')
    print('\tt1 - Force scan ports skipping discovery phase using known vpn ports.')
    print('\tt2 - Force scan ports skipping discovery phase using ports supplied in parameter(slow)')
    print('\tv - Force version detection on sS and sU. (intrusive)')
    print('\nReporting:')
    print('\tc - Include closed port on the the report.')
    print('\tn - Exludes results with no-response reason.')
    print('\nOthers:')
    print('\te - Automatically execute seekconvert.py after the scan is complete.')
    print('\nNOTE:\nThis script uses python-nmap module.')
    print('This script will automatically erase the content of the file if it is already existing.\n\n')
    return


# VARIABLES ----------------------------------------------
# NOTE: --version-light		: enable service version detection l2 in order to make it faster.
# 							  However, it may not be as detailed. Remove this if you do not need it.
#  		--max-rtt-timeout	: Adjust the time depending on how fast you want it to be.
#  							  Lower time outs might provide inaccurate result
# 		--scan-delay		: This is added in order to avoid firewall detection, each thread will supposedly send probe every
# 							  seconds specified by this option. It will also affect speed. Remove/Adjust if you are concern about the speed
# 							  Change it to 1s if you want it to scan 1 port every second.
# 							  COMMENT:
# 		-ddd				: I added this so it will include closed port on the text file.
# 							  If you remove this, it will only show open and filter
#
# You can also add any nmap arguments in the port_add_args. If you want to add argument specifically on a certain scan, 
# append it on the scan type that you want on nmap_args (ex. -sV --version-light). Just be careful of the spacing
scanner = NmapWaitForMe()
pool_lock = threading.Lock()
nmap_args = []
ports_prot = {'tcp': 'tcp', 'udp': 'udp', 'gre': 'gre', 'ip': 'ip'}
known_vpn_port = '47,67,68,443,500,547,1701,1723,1812,4500,7250,10000'
port_add_args = ' -n --max-retries 2 --max-rtt-timeout 800ms --min-hostgroup 256 --min_parallelism 50 --max_parallelism 700'

# MAIN ---------------------------------------------------
# Syntax format: seeker <ip> <port> <filename> <optional:full>
#        NOTE: full option triggers port scanning. This method will take time
#              This script uses "python-nmap" module
if __name__ == '__main__':
    print('\nseeker version 1.41')
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        display_usage()
    else:
        dt_start = datetime.datetime.now()
        print('Stopping previous nmap process')
        os.system('killall nmap')

        # Check if -Pn option is needed
        if len(sys.argv) == 5 and sys.argv[4].find('t') != -1:
            # Forced scan (skip discovery) on TCP Syn and UPD
            if len(sys.argv) == 5 and sys.argv[4].find('v') != -1:
                if len(sys.argv) == 5 and sys.argv[4].find('t1') != -1:
                    nmap_args.append('-sU -sV')
                    nmap_args.append('-sV')
                    nmap_args.append('-Pn -sU -sV')
                    nmap_args.append('-Pn -sV')
                else:
                    nmap_args.append('-sU -sV -Pn')
                    nmap_args.append('-sV -Pn')
            else:
                if len(sys.argv) == 5 and sys.argv[4].find('t1') != -1:
                    nmap_args.append('-sS')
                    nmap_args.append('-sU')
                    nmap_args.append('-Pn -sU ')
                    nmap_args.append('-Pn -sV ')
                else:
                    nmap_args.append('-Pn -sS ')
                    nmap_args.append('-Pn -sU ')
        else:
            # Normal Scan
            if len(sys.argv) == 5 and sys.argv[4].find('v') != -1:
                nmap_args.append('-sV')
                nmap_args.append('-sU -A')
            else:
                nmap_args.append('-sS')
                nmap_args.append('-sU')

        # Check Parameters------------------------------------
        # Protocol Scan. This triggers if option p is enabled
        if len(sys.argv) == 5 and sys.argv[4].find('p') != -1:
            # Protocol Scanning
            nmap_args.append('-sO')

        # Include connect scan -sT
        if len(sys.argv) == 5 and sys.argv[4].find('o') != -1:
            nmap_args.append('-sT')

        # Append Null and Fin on the scan
        nmap_args.append('-sN')
        nmap_args.append('-sF')

        # Include closed port
        if len(sys.argv) == 5 and sys.argv[4].find('c') != -1:
            port_add_args += ' -ddd'

        # Write nmap command info-----------------------------------------
        f = open(sys.argv[3], 'w')
        f.writelines('time                                                                    \n')
        f.writelines('\nCommands: \n')
        if len(sys.argv) == 5:
            f.writelines(sys.argv[0] + ' ' + sys.argv[1] + ' ' + sys.argv[2] + ' ' + sys.argv[3] + ' ' + sys.argv[4])
        else:
            f.writelines(sys.argv[0] + ' ' + sys.argv[1] + ' ' + sys.argv[2] + ' ' + sys.argv[3])
        f.writelines('\nNmap will execute the following:\n')
        for args in nmap_args:
            f.write('nmap ' + sys.argv[1] + ' ' + sys.argv[2] + ' ' + args + port_add_args + '\n')
        f.write('\nIP\tPROTOCOL\tPORT\tPORT-STATUS\tVERSION\tSCAN-TYPE\tPORT-REASON\tEXEC-TIME\n')
        f.flush()

        # Start Scan
        pool = ThreadPool(18)
        pool.map(scan_port, nmap_args)
        pool.close()
        pool.join()
        f.close()

        # Adding time stamp
        with open(sys.argv[3], 'r+') as ft:
            ft.seek(0)
            timestamp = (datetime.datetime.utcnow() - dt_start)
            ft.write(str(timestamp))

        print('\nDone!\n')

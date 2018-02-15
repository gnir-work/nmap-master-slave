# README #
### What is this repository for? ###

This is a basic master-slaves design for running multiple nmap scans.
The design:
There is a master which holds a list of ips to scan.
The master can recieve a number of parameters which will effect what scans will be run.
At the end of all of the scans the master will send a mail to the defined emails (in `consts.py`)

## Configuration
Most of the script configuration is located in `consts.py` and are quite straightforward.

## Parameters that can be passed to master
* The default is running the following 4 scans: -sS, -sU, -sN -sF
* `p` parameter will add another scan: -sO
* `t1` parameter will change -sS to -sS-Pn -sU to -sU-Pn using a predifined list of known vpn ports 
* `t2` parameter will change -sS to -sS-Pn -sU to -sU-Pn using the ports you specified
* `o` parameter will add anohter scanL -sT
* `v` includes service version: -sV
* `c` This will save to db both closed and open ports (By default its only open)
* `n` this will filter and exlude those ports with "no-response" status

## How do I get set up?
* pip install -r requirments.txt
* sudo apt-get install nmap

The slaves and master assume that there is a mysql server running in which they will save the scan results.
The configurations of db are in `consts.py` (user, password, server host, etc..)

## Running the slaves
When running the slaves you will be asked to pass the port on which the slaves will listen.
In order for the master to know about the slave you will need to add the port to `SLAVE_PORTS` list in `master.py`

## Examples
on slave machine: ```python3 slave.py -i 5555```
on master: ```python3 master.py```
This will start the master which will send the slave each time a different ip to scan.

NOTE: it doesn't matter if the master is run first or the slaves, and as a matter of fact you can leave the slaves on and run the master
as many times as you want with different ips and parameters.


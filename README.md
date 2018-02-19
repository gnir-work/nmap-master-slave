# README #
### What is this repository for? ###

This is a basic master-slave design pattern for running multiple nmap scans.
### Design:
There is a master which holds a list of ips to scan.
The master can receive a number of parameters which will effect which scans will be run.
The master has two types of queues:

* Report queue, a queue from which the master receives reports from all of the slaves
* Push queue, through this queue a master sends missions to the slave (There is a queue per slave)

At the end of all of the scans the master will send a mail to the defined emails (in `consts.py`)

## Configuration
Most of the script configuration is located in `consts.py` and are quite straightforward.
For example:
* The host of the sql db
* The ip of the master
* The email account information from which the emails will be sent
* The logging
* The port of the report queue 

One thing which is configurable (and must be updated) and isn't in `consts.py` are the ports of the slaves
They are located in `master.py` as they are not a const by definition.

___side note___: _This design pattern was chosen because we wanted to have full control over which slave
will receive which task and we couldn't get that functionality from a single push queue because
of how zmq works_

__side note 2__:  _There might be a second implementation where the master will be a rest api server and the slaves
will talk with it via __HTTP__, in case there will be it will be implemented on a different branch (probably implemented in flask)._


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
When running the slaves you will be asked to pass the port on which the slave will listen via the argument `-p`.

**PLEASE NOTE:** In order for the master to know about the slave you will need to **add the port** to `SLAVE_PORTS` list in `master.py`

## Running the master
When running the master you will be asked to pass several flags:

* `-f`, `--file` -> The name of the file which will contain the list of ips (can be relative or absolute path)
* `--divide` -> A flag which indicates whether an ips range should be a single job for one slave or should the master divide the range to single ips and each ip will be considered a job for a slave (default `True`)
* `--flags` -> The parameters that were explained the __parameters section__ above.
* `-p`, `--ports` -> The ports that will be scanned in the nmap scan.

## Examples
#### on first slave machine: 
```bash
python3 slave.py -i 5555
```
#### on second slave machine:
```bash
python3 slave.py -i 5556
```
#### on master: 
```bash
python3 master.py -f ips_to_scan.txt --flags pc --ports  3000-6000
```

#### in master.py 
```python
# This is important and very error prone!
SLAVE_PORTS = [5555, 5556]
```

#### ips_to_scan.txt:
```bash
127.0.0.1
159.122.141.152/29
```

This will start the master which will send each slave each time a different ip to scan (in a cycle).

__NOTE:__ if you will pass the `--divide` flag to the master than the ip `159.122.141.152/29` will be
divided to several ips (`159.122.141.152`, `159.122.141.153`, ..., `159.122.141.159`)

__NOTE:__ It doesn't matter if the master is run first or the slaves, and as a matter of fact you can leave the slaves on and run the master
as many times as you want with different ips and parameters. However it is recommended to start all of the slaves first.


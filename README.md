# README #
### What is this repository for? ###

This is a basic master-slaves design for running multiple nmap scans.
### The design:
There is a master which holds a list of ips to scan.
The master can receive a number of parameters which will effect what scans will be run.
The master has two types of queue:

* report queue, a queue from which the master will receive reports from all of the slaves
* push queue, through this queue a master will send missions to the slave (Their is a queue per slave)

At the end of all of the scans the master will send a mail to the defined emails (in `consts.py`)

## Configuration
Most of the script configuration is located in `consts.py` and are quite straightforward.
For example:
* The host of the sql db
* The ip of the master
* The email account information from which the emails will be sent
* The logging
* The port of the report queue 

One thing which is configurable (and must be updated) however isn't in `consts.py` are the ports of the slaves
They are located in `master.py` as they are not a const by definition.

___side note___: _This design pattern was chosen because we wanted to have full control over what slave
will receive what task and we couldn't get that from a single queue for pushing the tasks to the slave because
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


## Setting up the mysql server
__For a detailed guide go to__: https://www.copahost.com/blog/grant-mysql-remote-access/

####quick run through:

Step for setting up mysql server:
* First you need to edit the configuration file and replace the line `bind-address  = 127.0.0.1` to `bind-address   = 0.0.0.0`
    * on debian 9 the file is located at: /etc/mysql/mysql.conf.d/mysqld.cnf
    * on centos7.x by default the file is located at: /etc/my.cnf
    * _note_: on centos7.x you can run the command in order to find the conf file: `/usr/libexec/mysqld --help --verbose` which will output a lot of text, look for the line: `Default options are read from the following files in the given order:`
* Restart the mysql server:
    * On debian 9 and centos7.x: 
        * `systemctl stop mysql` 
        * `systemctl start mysql`
* Setup a user for remote connection:
    * connect to the mysql server by running `mysql -u root -p`, afterwards you will be prompted for the root password you chose on setup.
    * Run the following command (This will create a user with root privileges): 
    ```mysql
    GRANT ALL PRIVILEGES ON *.* TO '[user-name]'@'%'      
    IDENTIFIED BY '[new-password]';
    FLUSH PRIVILEGES;
    ```


## Running the slaves
When running the slaves you will be asked to pass the port on which the slaves will listen.

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
divided to several ips `159.122.141.152`, `159.122.141.153`, ..., `159.122.141.159`)

__NOTE:__ It doesn't matter if the master is run first or the slaves, and as a matter of fact you can leave the slaves on and run the master
as many times as you want with different ips and parameters. However it is recommended to start all of the slaves first.

## Error handling
In case a slave got an exception while handling an ip to scan it will report to master prior to exiting,
the master will than remove the slave from the list of active slaves and resend all of the ips that were sent to the
dead slave that were not yet completed (including the current ip on which the slave failed).

__NOTE:__ The slave will die on every exception!
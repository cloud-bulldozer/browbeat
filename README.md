# Browbeat
Scripts to help determine number of workers a given OpenStack service needs.

# Before running browbeat
* Execute the ansible/gen_hostfile.sh script (builds the ssh config)
* Install Tools (rally , shaker, connmon, etc)
* Configure browbeat-config to match your tests

# How to run Browbeat?
On the Red Hat OpenStack Director host, as the Stack user jump into a venv w/ Rally and you simply run:

    ./browbeat.sh <test name>

# What is necessary?
* Red Hat OpenStack Director
  * Why? We use the keyless ssh to reach each controller instance and compute instance.
* OpenStack Rally
  * Why? We are using Rally to stress the control plane of the env.
* Ansible
  * Why? We started with using bash to make changes to the Overcloud, creating complex sed/awks that we get for free with Ansible (for the most part). If you prefer to not use Ansible, the older versions (no longer maintained) of the browbeat.sh can be found here.


# Example Install, Check and Run

Installing Browbeat and running the performance checks can be performed either from your local machine or from the undercloud.  The local machine install assumes you have ansible already installed.

## Install Browbeat from your local machine
```
$ ssh-copy-id stack@<undercloud-ip>
$ git clone https://github.com/jtaleric/browbeat.git
$ cd browbeat/ansible
$ ./gen_hostfile.sh <undercloud-ip> ~/.ssh/config
$ ansible-playbook -i hosts install/browbeat.yml
```

## (Optional) Install shaker:
```
$ ansible-playbook -i hosts install/shaker.yml
```

## (Optional) Install connmon:
```
$ ansible-playbook -i hosts install/connmon.yml
```

## (Optional) Install pbench:
```
$ ansible-playbook -i hosts install/connmon.yml
```
* pbench install is under improvement at this time and likely requires additional setup to complete install.

## Next step is to run basic performance checks
```
$ ansible-playbook -i hosts check/site.yml
```
Your performance check output is located in check/bug_report.log

## Last step is to run performance stress tests through browbeat on the undercloud:
```
$ ssh undercloud-root
[root@ospd ~]# su - stack
[stack@ospd ~]$ screen -S browbeat
[stack@ospd ~]$ . browbeat-venv/bin/activate
(browbeat-venv)[stack@ospd ~]$ cd browbeat/
(browbeat-venv)[stack@ospd browbeat]$ vi browbeat.cfg # Edit browbeat.cfg to control how many stress tests are run.
(browbeat-venv)[stack@ospd browbeat]$ ./browbeat.sh test01
...
(browbeat-venv)[stack@ospd browbeat]$ ./graphing/rallyplot.py test01
```

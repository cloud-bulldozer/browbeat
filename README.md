Table of Contents
=================

  * [Browbeat](#browbeat)
  * [Before running browbeat](#before-running-browbeat)
  * [How to run Browbeat?](#how-to-run-browbeat)
  * [What is necessary?](#what-is-necessary)
  * [Detailed Install, Check and Run](#detailed-install-check-and-run)
    * [Install Browbeat from your local machine](#install-browbeat-from-your-local-machine)
      * [From your local machine:](#from-your-local-machine)
      * [(Optional) Install shaker:](#optional-install-shaker)
      * [(Optional) Install connmon:](#optional-install-connmon)
      * [Run performance checks](#run-performance-checks)
      * [Run performance stress tests through browbeat on the undercloud:](#run-performance-stress-tests-through-browbeat-on-the-undercloud)
    * [Install Browbeat directly on undercloud:](#install-browbeat-directly-on-undercloud)
      * [From your undercloud:](#from-your-undercloud)
      * [(Optional) Install shaker:](#optional-install-shaker-1)
      * [(Optional) Install connmon:](#optional-install-connmon-1)
      * [Run performance checks](#run-performance-checks-1)
      * [Run performance stress tests through browbeat:](#run-performance-stress-tests-through-browbeat)
  * [Running PerfKitBenchmarker](#running-perfkitbenchmarker)
  * [Contributing](#contributing)

# Browbeat
This started as a project to help determine the number of database connections a given OpenStack deployment uses via stress tests. It has since grown into a set of Ansible playbooks to help check deployments for known issues, install tools and change parameters of the overcloud.

# Before running browbeat
* Execute the ansible/gen_hostfile.sh script (builds the ssh config)
* Install Tools (connmon, collectd, graphite, grafana)
* Configure browbeat-config.yaml to match your tests

# How to run Browbeat?
On the Red Hat OpenStack Director host, as the Stack user jump into the browbeat venv and you simply run:

    ./browbeat.py --help

# What is necessary?
* Red Hat OpenStack Director
  * Why? We use passwordless ssh to reach each controller instance and compute instance.
* OpenStack Rally
  * Why? We are using Rally to stress the control plane of the env.
* Ansible
  * Why? We started with using bash to make changes to the Overcloud, creating complex sed/awks that we get for free with Ansible (for the most part). If you prefer to not use Ansible, the older versions (no longer maintained) of the browbeat.sh can be found in a older commit.


# Detailed Install, Check and Run

Installing Browbeat and running the Overcloud checks can be performed either from your local machine or from the undercloud.  The local machine install/check assumes you have ansible installed already.

## Install Browbeat from your local machine

### From your local machine:
```
$ ssh-copy-id stack@<undercloud-ip>
$ git clone https://github.com/jtaleric/browbeat.git
$ cd browbeat/ansible
$ ./gen_hostfile.sh <undercloud-ip> ~/.ssh/config
$ vi install/group_vars/all # Make sure to edit the dns_server to the correct ip address
$ ansible-playbook -i hosts install/browbeat.yml
$ vi install/group_vars/all # Edit browbeat subnet/start/end/gw settings
$ ansible-playbook -i hosts install/browbeat_network.yml
$ ansible-playbook -i hosts install/shaker_build.yml
```

### (Optional) Install collectd:
```
$ ansible-playbook -i hosts install/collectd.yml
```

### (Optional) Install connmon:
```
$ ansible-playbook -i hosts install/connmon.yml
```

### Run Overcloud checks
```
$ ansible-playbook -i hosts check/site.yml
```
Your Overcloud check output is located in check/bug_report.log

### Run performance stress tests through browbeat on the undercloud:
```
$ ssh undercloud-root
[root@ospd ~]# su - stack
[stack@ospd ~]$ screen -S browbeat
[stack@ospd ~]$ . browbeat-venv/bin/activate
(browbeat-venv)[stack@ospd ~]$ cd browbeat/
(browbeat-venv)[stack@ospd browbeat]$ vi browbeat-config.yaml # Edit browbeat-config.yaml to control how many stress tests are run.
(browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py -w
```

## Install Browbeat directly on undercloud:

### From your undercloud:
```
$ ssh undercloud-root
[root@ospd ~]# su - stack
[stack@ospd ~]$ git clone https://github.com/jtaleric/browbeat.git
[stack@ospd ~]$ cd browbeat/ansible
[stack@ospd ansible]$ ./gen_hostfile.sh localhost ~/.ssh/config
[stack@ospd ansible]$ sudo easy_install pip
[stack@ospd ansible]$ sudo pip install ansible
[stack@ospd ansible]$ vi install/group_vars/all # Make sure to edit the dns_server to the correct ip address
[stack@ospd ansible]$ ansible-playbook -i hosts install/browbeat.yml
[stack@ospd ansible]$ vi install/group_vars/all # Edit browbeat public/private subnet/start/end/gw settings
[stack@ospd ansible]$ ansible-playbook -i hosts install/browbeat_network.yml
[stack@ospd ansible]$ ansible-playbook -i hosts install/shaker_build.yml
```

### (Optional) Install collectd:
```
[stack@ospd ansible]$ ansible-playbook -i hosts install/collectd.yml
```

### (Optional) Install connmon:
```
[stack@ospd ansible]$ ansible-playbook -i hosts install/connmon.yml
```

### Run Overcloud checks
```
[stack@ospd ansible]$ ansible-playbook -i hosts check/site.yml
```
Your Overcloud check output is located in check/bug_report.log

### Run performance stress tests through browbeat:
```
[stack@ospd ansible]$ . ../../browbeat-venv/bin/activate
(browbeat-venv)[stack@ospd ansible]$ cd ..
(browbeat-venv)[stack@ospd browbeat]$ vi browbeat-config.yaml # Edit browbeat.cfg to control how many stress tests are run.
(browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py -w
```

# Running PerfKitBenchmarker

Work is on-going to utilize PerfKitBenchmarker as a workload provider to browbeat.  Many benchmarks work out of the box with browbeat.  You must ensure that your network is setup correctly to run those benchmarks and you will need to configure the settings in ansible/install/group_vars/all for browbeat public/private networks. Currently  tested benchmarks include: bonnie++, cluster_boot, copy_throughput(cp,dd,scp), fio, iperf, netperf, mesh_network, mongodb_ycsb, ping, and sysbench_oltp.

To run browbeat's PerfKit Benchmarks, you can start by viewing the tested benchmark's configuration in conf/browbeat-perfkit-complete.yaml. You must add them to your specific browbeat config yaml file or enable/disable the benchmarks you wish to run in the default config file (browbeat-config.yaml).  There are many flags exposed in the configuration files to tune how those benchmarks run.  Additional flags are exposed in the soruce code of PerfKitBenchmarker available: https://github.com/GoogleCloudPlatform/PerfKitBenchmarker

Example running only PerfKitBenchmarker benchmarks with browbeat from browbeat-config.yaml:
```
(browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py -w perfkit -s browbeat-config.yaml
```

# Contributing
Contributions are most welcome! Pull requests need to be submitted using the gerrit code review system. Firstly, you need to login to GerritHub using your GitHub credentials and need to authorize GerritHub to access your account. Once you are logged in click you user name in the top-right corner, go to  'Settings' and under 'SSH Public Keys' you need to paste your public key. You can view your public key using:
```
$ cat ~/.ssh/id_\{r or d\}sa.pub
```
Set your username and email for git:
```
$ git config --global user.email "example@example.com"
$ git config --global user.name "example"
```
Next, Clone the github repository:
```
$ git clone https://github.com/jtaleric/browbeat.git
```
You need to have git-review in order to be able to submit patches using the gerrit code review system. You can install it using:
```
$ yum install git-review
```
To set up your cloned repository to work with gerrit:
```
[user@laptop browbeat]$ git review -s
```
Make your changes and then commit them. Use:
```
[user@laptop browbeat]$ git review
```
The first time you are submitting a patch, you will be requested for a user name which is typically your GerritHub user name(same as GitHub user name).

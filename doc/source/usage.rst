========
Usage
========

Run Overcloud checks
--------------------

::

    $ ansible-playbook -i hosts check/site.yml

Your Overcloud check output is located in results/bug_report.log

NOTE: It is strongly advised to not run the ansible playbooks in a venv.

Run performance stress tests through Browbeat on the undercloud:
----------------------------------------------------------------

::

    $ ssh undercloud-root
    [root@ospd ~]# su - stack
    [stack@ospd ~]$ screen -S browbeat
    [stack@ospd ~]$ . browbeat-venv/bin/activate
    (browbeat-venv)[stack@ospd ~]$ cd browbeat/
    (browbeat-venv)[stack@ospd browbeat]$ vi browbeat-config.yaml # Edit browbeat-config.yaml to control how many stress tests are run.
    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py <workload> #perfkit, rally, shaker or "all"


Run performance stress tests through Browbeat
---------------------------------------------

::

    [stack@ospd ansible]$ . ../../browbeat-venv/bin/activate
    (browbeat-venv)[stack@ospd ansible]$ cd ..
    (browbeat-venv)[stack@ospd browbeat]$ vi browbeat-config.yaml # Edit browbeat.cfg to control how many stress tests are run.
    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py <workload> #perfkit, rally, shaker or "all"

Running PerfKitBenchmarker
==========================

Work is on-going to utilize PerfKitBenchmarker as a workload provider to
Browbeat. Many benchmarks work out of the box with Browbeat. You must
ensure that your network is setup correctly to run those benchmarks and
you will need to configure the settings in
ansible/install/group_vars/all.yml for Browbeat public/private
networks. Currently tested benchmarks include: aerospike, bonnie++,
cluster_boot, copy_throughput(cp,dd,scp), fio, iperf, mesh_network,
mongodb_ycsb, netperf, object_storage_service, ping, scimark2, and
sysbench_oltp.

To run Browbeat's PerfKit Benchmarks, you can start by viewing the
tested benchmark's configuration in conf/browbeat-perfkit-complete.yaml.
You must add them to your specific Browbeat config yaml file or
enable/disable the benchmarks you wish to run in the default config file
(browbeat-config.yaml). There are many flags exposed in the
configuration files to tune how those benchmarks run. Additional flags
are exposed in the source code of PerfKitBenchmarker available on the
Google Cloud Github_.

.. _Github: https://github.com/GoogleCloudPlatform/PerfKitBenchmarker

Example running only PerfKitBenchmarker benchmarks with Browbeat from
browbeat-config.yaml:

::

    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py  perfkit -s browbeat-config.yaml

Working with Multiple Clouds
============================

If you are running playbooks from your local machine you can run against more
than one cloud at the same time.  To do this, you should create a directory
per-cloud and clone Browbeat into that specific directory:

::

    [browbeat@laptop ~]$ mkdir cloud01; cd cloud01
    [browbeat@laptop cloud01]$ git clone git@github.com:openstack/browbeat.git
    ...
    [browbeat@laptop cloud01]$ cd browbeat/ansible
    [browbeat@laptop ansible]$ ./generate_tripleo_hostfile.sh <cloud01-ip-address>
    [browbeat@laptop ansible]$ ansible-playbook -i hosts (Your playbook you wish to run...)
    [browbeat@laptop ansible]$ ssh -F ssh-config overcloud-controller-0  # Takes you to first controller

Repeat the above steps for as many clouds as you have to run playbooks against your clouds.

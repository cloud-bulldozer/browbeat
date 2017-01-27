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

Running Shaker
==============
Running Shaker requires the shaker image to be built, which in turn requires
instances to be able to access the internet. The playbooks for this installation
have been described in the installation documentation but for the sake of
convenience they are being mentioned here as well.

::

    $ ansible-playbook -i hosts install/browbeat_network.yml
    $ ansible-playbook -i hosts install/shaker_build.yml

.. note:: The playbook to setup networking is provided as an example only and
    might not work for you based on your underlay/overlay network setup. In such
    cases, the exercise of setting up networking for instances to be able to access
    the internet is left to the user.

Once the shaker image is built, you can run Shaker via Browbeat by filling in a
few configuration options in the configuration file. The meaning of each option is
summarized below:

**shaker:**
   :enabled: Boolean ``true`` or ``false``, enable shaker or not
   :server: IP address of the shaker-server for agent to talk to (undercloud IP
    by default)
   :port: Port to connect to the shaker-server (undercloud port 5555 by default)
   :flavor: OpenStack instance flavor you want to use
   :join_timeout: Timeout in seconds for agents to join
   :sleep_before: Time in seconds to sleep before executing a scenario
   :sleep_after: Time in seconds to sleep after executing a scenario
   :venv: venv to execute shaker commands in, ``/home/stack/shaker-venv`` by
    default
   :shaker_region: OpenStack region you want to use
   :external_host: IP of a server for  external tests (should have
    ``browbeat/util/shaker-external.sh`` executed on it previously and have
    iptables/firewalld/selinux allowing connections on the ports used by network
    testing tools netperf and iperf)

   **scenarios:** List of scenarios you want to run
       :\- name: Name for the scenario. It is used to create directories/files
             accordingly
       :enabled: Boolean ``true`` or ``false`` depending on whether or not you
        want to execute the scenario
       :density: Number of instances
       :compute: Number of compute nodes across which to spawn instances
       :placement: ``single_room`` would mean one instance per compute node and
        ``double_room`` would give you two instances per compute node
       :progression: ``null`` means all agents are involved, ``linear`` means
        execution starts with one agent and increases linearly, ``quadratic``
        would result in quadratic growth in number of agents participating
        in the test concurrently
       :time: Time in seconds you want each test in the scenario
        file to run
       :file: The base shaker scenario file to use to override
        options (this would depend on whether you want to run L2, L3 E-W or L3
        N-S tests and also on the class of tool you want to use such as flent or
        iperf3)

To analyze results sent to Elasticsearch (you must have Elasticsearch enabled
and the IP of the Elasticsearch host provided in the browbeat configuration
file), you can use the following playbook to setup some prebuilt dashboards for
you:

::

    $ ansible-playbook -i hosts install/kibana-visuals.yml

Alternatively you can create your own visualizations of specific shaker runs
using some simple searches such as:

::

   shaker_uuid: 97092334-34e8-446c-87d6-6a0f361b9aa8 AND record.concurrency: 1 AND result.result_type: bandwidth
   shaker_uuid: c918a263-3b0b-409b-8cf8-22dfaeeaf33e AND record.concurrency:1 AND record.test:Bi-Directional


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

========
Usage
========

- No longer Maintained since Pike -  Run Overcloud checks
----------------------------------------------------------

::

    $ ansible-playbook -i hosts check/site.yml

Your Overcloud check output is located in results/bug_report.log

NOTE: It is strongly advised to not run the ansible playbooks in a virtual environment.

Run Browbeat performance tests from Undercloud
----------------------------------------------

::

    $ ssh undercloud-root
    [root@ospd ~]# su - stack
    [stack@ospd ~]$ cd browbeat/
    [stack@ospd browbeat]$ . .browbeat-venv/bin/activate
    (browbeat-venv)[stack@ospd browbeat]$ vi browbeat-config.yaml # Edit browbeat-config.yaml to control how many stress tests are run.
    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py <workload> #perfkit, rally, shaker or "all"

Running PerfKitBenchmarker
---------------------------

Many benchmarks work out of the box with Browbeat. You must ensure that your
network is setup correctly to run those benchmarks. Currently tested benchmarks
include: aerospike, bonnie++, cluster_boot, copy_throughput(cp,dd,scp), fio,
iperf, mesh_network, mongodb_ycsb, netperf, object_storage_service, ping,
scimark2, and sysbench_oltp.

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

    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py perfkit -s browbeat-config.yaml

Running Shaker
---------------

Running Shaker requires the shaker image to be built, which in turn requires
instances to be able to access the internet. The playbooks for this installation
have been described in the installation documentation but for the sake of
convenience they are being mentioned here as well.

::

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

Running YODA
------------

YODA (Yet Openstack Deployment tool, Another) is a workload integrated into
Browbeat for benchmarking TripleO deployment.  This includes importing baremetal
nodes, running introspections and overcloud deployements of various kinds. Note
that YODA assumes it is on the undercloud of a TripleO instance post undercloud
installation and introspection.

Configuration
~~~~~~~~~~~~~

For examples of the configuration see `browbeat-complete.yaml` in the repo root directory.
Additional configuration documentation can be found below for each subworkload of YODA.

Overcloud
~~~~~~~~~

For overcloud workloads, note that the nodes dictionary is dynamic, so you don't
have to define types you aren't using, this is done in the demonstration
configurations for the sake of completeness. Furthermore the node name is taken
from the name of the field, meaning custom role names should work fine there.

The step parameter decides how many nodes can be distributed between the various
types to get from start scale to end scale, if these are the same it won't
matter. But if they are different up to that many nodes will be distributed to
the different node types (in no particular order) before the next deploy is
performed. The step rule is violated if and only if it is required to keep the
deployment viable, for example if the step dictates that 2 control nodes be
deployed it will skip to 3 even if it violates step.

YODA has basic support for custom templates and more advanced roles, configure the
`templates:` paramater in the overcloud benchmark section with a string for
template paths.

        templates: "-e /usr/share/openstack-tripleo-heat-templates/environments/network-isolation.yaml"

Note that `--templates` is passed to the `overcloud deploy` command before this,
then nodes sizes, ntp server and timeout are passed after, so your templates
will override the defaults, but not scale, timeout, or ntp settings from the
YODA config.  If you want to use scheduling hints for your overcloud deploy you
will need to pip install [ostag](https://github.com/jkilpatr/ostag) and set
`node_pinning: True` in your config file. Ostag will be used before every deploy
to clean all tags and tag the appropriate nodes. If you set `node_pinning: False`
tags will be cleaned before the deploy. If you need more advanced features view
the ostag readme for how to tag based on node properties. If you don't want YODA
to edit your node properties, don't define `node_pinning` in your configuration.

Introspection
~~~~~~~~~~~~~

Introspection workloads have two modes, batch and individual, the batch workload
follows the documentation exactly, nodes are imported, then bulk introspection
is run. Individual introspection has it's own custom batch size and handles
failures more gracefully (individual instead of group retries). Both have a
timeout configured in seconds and record the amount of time required for each
node to pxe and the number of failures.

`timeout` is how long we wait for the node to come back from introspection this is
hardware variable. Although the default 900 seconds has been shown to be the 99th
percentile for success across at least two stes of hardware. Adjust as required.

Note that `batch_size` can not produce a batch of unintrospected ndoes if none exist
so the last batch may be below the maximum size. When nodes in a batch fail the `failure_count`
is incremented and the nodes are returned to the pool. So it's possible that same node will
fail again in another batch. There is a safety mechanism that will kill Yoda if a node exceeds
10 retries as that's pretty much garunteed to be misconfigured. For bulk introspection all nodes
are tried once and what you get is what you get.

If you wish to change the introspection workload failure threshold of 10% you can
set `max_fail_amnt` to any floating point value you desire.

I would suggest bulk introspection for testing documented TripleO workflows and
individual introspection to test the performance of introspection itself.

Interpreting Browbeat Results
-----------------------------

By default results for each test will be placed in a timestamped folder `results/` inside your Browbeat folder.
Each run folder will contain output files from the various workloads and benchmarks that ran during that Browbeat
run, as well as a report card that summarizes the results of the tests.

Browbeat for the most part tries to restrict itself to running tests, it will only exit with a nonzero return code
if a workload failed to run. If, for example, Rally where to run but not be able to boot any instances on your cloud
Browbeat would return with RC 0 without any complaints, only by looking into the Rally results for that Browbeat run
would you determine that your cloud had a problem that made benchmarking it impossible.

Likewise if Rally manages to run at a snails pace, Browbeat will still exit without complaint. Be aware of this when
running Browbeat and take the time to either view the contents of the results folder after a run. Or setup Elasticsearch
and Kibana to view them more easily.


Working with Multiple Clouds
----------------------------

If you are running playbooks from your local machine you can run against more
than one cloud at the same time.  To do this, you should create a directory
per-cloud and clone Browbeat into that specific directory:

::

    [browbeat@laptop ~]$ mkdir cloud01; cd cloud01
    [browbeat@laptop cloud01]$ git clone git@github.com:openstack/browbeat.git
    ...
    [browbeat@laptop cloud01]$ cd browbeat/ansible
    [browbeat@laptop ansible]$ ./generate_tripleo_hostfile.sh -t <cloud01-ip-address>
    [browbeat@laptop ansible]$ ansible-playbook -i hosts (Your playbook you wish to run...)
    [browbeat@laptop ansible]$ ssh -F ssh-config overcloud-controller-0  # Takes you to first controller

Repeat the above steps for as many clouds as you have to run playbooks against your clouds.

Compare software-metadata from two different runs
-------------------------------------------------

Browbeat's metadata is great to help build visuals in Kibana by querying on specific metadata fields, but sometimes
we need to see what the difference between two builds might be. Kibana doesn't have a good way to show this, so we
added an option to Browbeat CLI to query ElasticSearch.

To use :

::

    $ python browbeat.py --compare software-metadata --uuid "browbeat-uuid-1" "browbeat-uuid-2"

Real world use-case, we had two builds in our CI that used the exact same DLRN hash, however the later build had a
10x performance hit for two Neutron operations, router-create and add-interface-to-router. Given we had exactly the
same DLRN hash, the only difference could be how things were configured. Using this new code, we could quickly identify
the difference -- TripleO enabled l3_ha.

Below is an example output of comparing metadata:

::

    +-------------------------------------------------------------------------------------------------------------------------------------+
    Host                 | Service              | Option               | Key                  | Old Value            | New Value
    +-------------------------------------------------------------------------------------------------------------------------------------+
    overcloud-controller-2 | nova                 | conductor            | workers              | 0                    | 12
    overcloud-controller-2 | nova                 | DEFAULT              | metadata_workers     | 0                    | 12
    overcloud-controller-2 | nova                 | DEFAULT              | my_ip                | 172.16.0.23          | 172.16.0.16
    overcloud-controller-2 | nova                 | DEFAULT              | enabled_apis         | osapi_compute,metadata | metadata
    overcloud-controller-2 | nova                 | DEFAULT              | osapi_compute_workers | 0                    | 12
    overcloud-controller-2 | nova                 | neutron              | region_name          | RegionOne            | regionOne
    overcloud-controller-2 | neutron-plugin       | ovs                  | local_ip             | 172.17.0.11          | 172.17.0.16
    overcloud-controller-2 | neutron-plugin       | securitygroup        | firewall_driver      | openvswitch          | iptables_hybrid
    overcloud-controller-2 | heat                 | DEFAULT              | num_engine_workers   | 0                    | 16
    overcloud-controller-2 | keystone             | admin_workers        | processes            | 32                   |
    overcloud-controller-2 | keystone             | admin_workers        | threads              | 1                    |
    overcloud-controller-2 | keystone             | eventlet_server      | admin_workers        | 8                    | 12
    overcloud-controller-2 | keystone             | eventlet_server      | public_workers       | 8                    | 12
    overcloud-controller-2 | keystone             | oslo_messaging_notifications | driver               | messaging            | messagingv2
    overcloud-controller-2 | keystone             | main_workers         | processes            | 32                   |
    overcloud-controller-2 | keystone             | main_workers         | threads              | 1                    |
    overcloud-controller-2 | keystone             | token                | provider             | uuid                 | fernet
    overcloud-controller-2 | rabbitmq             | DEFAULT              | file                 | 65436                |
    overcloud-controller-2 | mysql                | DEFAULT              | max                  | 4096                 |
    overcloud-controller-2 | cinder               | DEFAULT              | exec_dirs            | /sbin,/usr/sbin,/bin,/usr/bin | /sbin,/usr/sbin,/bin,/usr/bin,/usr/local/bin,/usr/local/sbin,/usr/lpp/mmfs/bin
    overcloud-controller-2 | cinder               | DEFAULT              | osapi_volume_workers | 32                   | 12
    overcloud-controller-2 | glance               | DEFAULT              | bind_port            | 9191                 | 9292
    overcloud-controller-2 | glance               | DEFAULT              | workers              | 32                   | 12
    overcloud-controller-2 | glance               | DEFAULT              | log_file             | /var/log/glance/registry.log | /var/log/glance/cache.log
    overcloud-controller-2 | glance               | ref1                 | auth_version         | 2                    | 3
    overcloud-controller-2 | glance               | glance_store         | stores               | glance.store.http.Store,glance.store.swift.Store | http,swift
    overcloud-controller-2 | glance               | glance_store         | os_region_name       | RegionOne            | regionOne
    overcloud-controller-2 | gnocchi              | metricd              | workers              | 8                    | 12
    overcloud-controller-2 | gnocchi              | storage              | swift_auth_version   | 2                    | 3
    overcloud-controller-2 | neutron              | DEFAULT              | global_physnet_mtu   | 1496                 | 1500
    overcloud-controller-2 | neutron              | DEFAULT              | rpc_workers          | 32                   | 12
    overcloud-controller-2 | neutron              | DEFAULT              | api_workers          | 32                   | 12
    overcloud-controller-1 | nova                 | conductor            | workers              | 0                    | 12
    overcloud-controller-1 | nova                 | DEFAULT              | metadata_workers     | 0                    | 12
    overcloud-controller-1 | nova                 | DEFAULT              | my_ip                | 172.16.0.11          | 172.16.0.23
    overcloud-controller-1 | nova                 | DEFAULT              | enabled_apis         | osapi_compute,metadata | metadata
    overcloud-controller-1 | nova                 | DEFAULT              | osapi_compute_workers | 0                    | 12
    overcloud-controller-1 | nova                 | neutron              | region_name          | RegionOne            | regionOne
    overcloud-controller-1 | neutron-plugin       | ovs                  | local_ip             | 172.17.0.15          | 172.17.0.11
    overcloud-controller-1 | neutron-plugin       | securitygroup        | firewall_driver      | openvswitch          | iptables_hybrid
    overcloud-controller-1 | heat                 | DEFAULT              | num_engine_workers   | 0                    | 16
    overcloud-controller-1 | keystone             | admin_workers        | processes            | 32                   |
    overcloud-controller-1 | keystone             | admin_workers        | threads              | 1                    |
    overcloud-controller-1 | keystone             | eventlet_server      | admin_workers        | 8                    | 12
    overcloud-controller-1 | keystone             | eventlet_server      | public_workers       | 8                    | 12
    overcloud-controller-1 | keystone             | oslo_messaging_notifications | driver               | messaging            | messagingv2
    overcloud-controller-1 | keystone             | main_workers         | processes            | 32                   |
    overcloud-controller-1 | keystone             | main_workers         | threads              | 1                    |
    overcloud-controller-1 | keystone             | token                | provider             | uuid                 | fernet
    overcloud-controller-1 | rabbitmq             | DEFAULT              | file                 | 65436                |
    overcloud-controller-1 | mysql                | DEFAULT              | max                  | 4096                 |
    overcloud-controller-1 | cinder               | DEFAULT              | exec_dirs            | /sbin,/usr/sbin,/bin,/usr/bin | /sbin,/usr/sbin,/bin,/usr/bin,/usr/local/bin,/usr/local/sbin,/usr/lpp/mmfs/bin
    overcloud-controller-1 | cinder               | DEFAULT              | osapi_volume_workers | 32                   | 12
    overcloud-controller-1 | glance               | DEFAULT              | bind_port            | 9191                 | 9292
    overcloud-controller-1 | glance               | DEFAULT              | workers              | 32                   | 12
    overcloud-controller-1 | glance               | DEFAULT              | log_file             | /var/log/glance/registry.log | /var/log/glance/cache.log
    overcloud-controller-1 | glance               | ref1                 | auth_version         | 2                    | 3
    overcloud-controller-1 | glance               | glance_store         | stores               | glance.store.http.Store,glance.store.swift.Store | http,swift
    overcloud-controller-1 | glance               | glance_store         | os_region_name       | RegionOne            | regionOne
    overcloud-controller-1 | gnocchi              | metricd              | workers              | 8                    | 12
    overcloud-controller-1 | gnocchi              | storage              | swift_auth_version   | 2                    | 3
    overcloud-controller-1 | neutron              | DEFAULT              | global_physnet_mtu   | 1496                 | 1500
    overcloud-controller-1 | neutron              | DEFAULT              | rpc_workers          | 32                   | 12
    overcloud-controller-1 | neutron              | DEFAULT              | api_workers          | 32                   | 12
    overcloud-controller-0 | nova                 | conductor            | workers              | 0                    | 12
    overcloud-controller-0 | nova                 | DEFAULT              | metadata_workers     | 0                    | 12
    overcloud-controller-0 | nova                 | DEFAULT              | my_ip                | 172.16.0.15          | 172.16.0.10
    overcloud-controller-0 | nova                 | DEFAULT              | enabled_apis         | osapi_compute,metadata | metadata
    overcloud-controller-0 | nova                 | DEFAULT              | osapi_compute_workers | 0                    | 12
    overcloud-controller-0 | nova                 | neutron              | region_name          | RegionOne            | regionOne
    overcloud-controller-0 | neutron-plugin       | ovs                  | local_ip             | 172.17.0.10          | 172.17.0.18
    overcloud-controller-0 | neutron-plugin       | securitygroup        | firewall_driver      | openvswitch          | iptables_hybrid
    overcloud-controller-0 | heat                 | DEFAULT              | num_engine_workers   | 0                    | 16
    overcloud-controller-0 | keystone             | admin_workers        | processes            | 32                   |
    overcloud-controller-0 | keystone             | admin_workers        | threads              | 1                    |
    overcloud-controller-0 | keystone             | eventlet_server      | admin_workers        | 8                    | 12
    overcloud-controller-0 | keystone             | eventlet_server      | public_workers       | 8                    | 12
    overcloud-controller-0 | keystone             | oslo_messaging_notifications | driver               | messaging            | messagingv2
    overcloud-controller-0 | keystone             | main_workers         | processes            | 32                   |
    overcloud-controller-0 | keystone             | main_workers         | threads              | 1                    |
    overcloud-controller-0 | keystone             | token                | provider             | uuid                 | fernet
    overcloud-controller-0 | rabbitmq             | DEFAULT              | file                 | 65436                |
    overcloud-controller-0 | mysql                | DEFAULT              | max                  | 4096                 |
    overcloud-controller-0 | cinder               | DEFAULT              | exec_dirs            | /sbin,/usr/sbin,/bin,/usr/bin | /sbin,/usr/sbin,/bin,/usr/bin,/usr/local/bin,/usr/local/sbin,/usr/lpp/mmfs/bin
    overcloud-controller-0 | cinder               | DEFAULT              | osapi_volume_workers | 32                   | 12
    overcloud-controller-0 | glance               | DEFAULT              | bind_port            | 9191                 | 9292
    overcloud-controller-0 | glance               | DEFAULT              | workers              | 32                   | 12
    overcloud-controller-0 | glance               | DEFAULT              | log_file             | /var/log/glance/registry.log | /var/log/glance/cache.log
    overcloud-controller-0 | glance               | ref1                 | auth_version         | 2                    | 3
    overcloud-controller-0 | glance               | glance_store         | stores               | glance.store.http.Store,glance.store.swift.Store | http,swift
    overcloud-controller-0 | glance               | glance_store         | os_region_name       | RegionOne            | regionOne
    overcloud-controller-0 | gnocchi              | metricd              | workers              | 8                    | 12
    overcloud-controller-0 | gnocchi              | storage              | swift_auth_version   | 2                    | 3
    overcloud-controller-0 | neutron              | DEFAULT              | global_physnet_mtu   | 1496                 | 1500
    overcloud-controller-0 | neutron              | DEFAULT              | rpc_workers          | 32                   | 12
    overcloud-controller-0 | neutron              | DEFAULT              | api_workers          | 32                   | 12
    +-------------------------------------------------------------------------------------------------------------------------------------+

Compare performance of two different runs
------------------------------------------
Using the CLI the user can determine, run to run performance differences. This is a good tool for spot checking performance of an OpenStack
release.

To use :

::

    $ python browbeat.py -q -u browbeat_uuid1 browbeat_uuid2

Example output from running this CLI command

::

    python browbeat.py -q -u 6b50b6f7-acae-445a-ac53-78200b5ba58c 938dc451-d881-4f28-a6cb-ad502b177f3b
    2018-07-13 14:38:49,516 - browbeat.config -    INFO - Config bs.yaml validated
    2018-07-13 14:38:49,646 - browbeat.elastic -    INFO - Making query against browbeat-rally-*
    2018-07-13 14:38:54,292 - browbeat.elastic -    INFO - Searching through ES for uuid: 6b50b6f7-acae-445a-ac53-78200b5ba58c
    2018-07-13 14:38:54,293 - browbeat.elastic -    INFO - Scrolling through Browbeat 336 documents...
    2018-07-13 14:38:54,432 - browbeat.elastic -    INFO - Making query against browbeat-rally-*
    2018-07-13 14:38:54,983 - browbeat.elastic -    INFO - Searching through ES for uuid: 938dc451-d881-4f28-a6cb-ad502b177f3b
    2018-07-13 14:38:54,983 - browbeat.elastic -    INFO - Scrolling through Browbeat 22 documents...
    +---------------------------------------------------------------------------------------------------------------------------------------------------------+
    Scenario                          | Action                                   | concurrency     | times           | 0b5ba58c   | 2b177f3b   | % Difference
    +---------------------------------------------------------------------------------------------------------------------------------------------------------+
    create-list-router                | neutron.create_router                    |             500 |              32 |     19.940 |     15.656 |       -21.483
    create-list-router                | neutron.list_routers                     |             500 |              32 |      2.588 |      2.086 |       -19.410
    create-list-router                | neutron.create_network                   |             500 |              32 |      3.294 |      2.366 |       -28.177
    create-list-router                | neutron.create_subnet                    |             500 |              32 |      4.282 |      2.866 |       -33.075
    create-list-router                | neutron.add_interface_router             |             500 |              32 |     12.741 |     10.324 |       -18.973
    create-list-port                  | neutron.list_ports                       |             500 |              32 |     52.627 |     43.448 |       -17.442
    create-list-port                  | neutron.create_network                   |             500 |              32 |      4.025 |      2.771 |       -31.165
    create-list-port                  | neutron.create_port                      |             500 |              32 |     19.458 |      5.412 |       -72.189
    create-list-security-group        | neutron.create_security_group            |             500 |              32 |      3.244 |      2.708 |       -16.514
    create-list-security-group        | neutron.list_security_groups             |             500 |              32 |      6.837 |      5.720 |       -16.339
    create-list-subnet                | neutron.create_subnet                    |             500 |              32 |     11.366 |      4.809 |       -57.689
    create-list-subnet                | neutron.create_network                   |             500 |              32 |      6.432 |      4.286 |       -33.368
    create-list-subnet                | neutron.list_subnets                     |             500 |              32 |     10.627 |      7.522 |       -29.221
    create-list-network               | neutron.list_networks                    |             500 |              32 |     15.154 |     13.073 |       -13.736
    create-list-network               | neutron.create_network                   |             500 |              32 |     10.200 |      6.595 |       -35.347
    +---------------------------------------------------------------------------------------------------------------------------------------------------------+
    +-----------------------------------------------------------------------------------------------------------------+
    UUID                                     | Version              | Build                | Number of runs
    +-----------------------------------------------------------------------------------------------------------------+
    938dc451-d881-4f28-a6cb-ad502b177f3b     | queens               | 2018-03-20.2         |                    1
    6b50b6f7-acae-445a-ac53-78200b5ba58c     | ocata                | 2017-XX-XX.X         |                    3
    +-----------------------------------------------------------------------------------------------------------------+

We can see from the output above that we also provide the user with some metadata regarding the two runs, like the amount version and the number of runs each UUID
contained.

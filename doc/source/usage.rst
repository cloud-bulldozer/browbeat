========
Usage
========

Run Browbeat performance tests from Undercloud
----------------------------------------------
For Running the workloads from Undercloud

::

    $ ssh undercloud-root
    [root@undercloud ~]# su - stack
    [stack@undercloud ~]$ cd browbeat/
    [stack@undercloud browbeat]$ . .browbeat-venv/bin/activate
    (.browbeat-venv)[stack@undercloud browbeat]$ vi browbeat-config.yaml # Edit browbeat-config.yaml to control how many stress tests are run.
    (.browbeat-venv)[stack@undercloud browbeat]$ ./browbeat.py <workload> #rally, shaker or "all"

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

    $ ansible-playbook -i hosts.yml install/kibana-visuals.yml

Alternatively you can create your own visualizations of specific shaker runs
using some simple searches such as:

::

   shaker_uuid: 97092334-34e8-446c-87d6-6a0f361b9aa8 AND record.concurrency: 1 AND result.result_type: bandwidth
   shaker_uuid: c918a263-3b0b-409b-8cf8-22dfaeeaf33e AND record.concurrency:1 AND record.test:Bi-Directional

Correlating test run with logs
------------------------------

If filebeat is enabled in the browbeat configuration file and filebeat was previously installed by running:

::

    $ ansible-playbook -i hosts.yml common_logging/install_logging.yml

as explained in the installation documentation, then

By enabling filebeat logging within the browbeat configuration file, a playbook `ansible/common_logging/browbeat_logging.yml`
is run which appends browbeat_uuid to log messages and starts filebeat pre-browbeat workload run so that log messages have
browbeat uuid appended and clears the uuid from the configuration file and stops filebeat from sending more logs post-browbeat
workload run



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

You'll need to install extra dependencies for browbeat insights, which will
provide additional modules needed for providing insights.

To install :

::

    $ source browbeat/.browbeat-venv/bin/activate
    $ pip install .[insights]

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

Cleanup Rally resources
------------------------------------------
Rally cleans up resources automatically at the end of testing. However, we disable cleanup in rally sometimes during testing and later try to manually delete these resources. Cleaning up the resources at scale is very time consuming, so we came up with a python process to speed up this activity.


To cleanup :

::

    $ source browbeat/.rally-venv/bin/activate
    $ source ~/overcloudrc
    $ python browbeat/rally_cleanup.py

Generate CSV file/Google Sheets from Rally json file
--------------------------------------------
Rally generates a json file with data about atomic actions duration from each iteration. These atomic actions often occur multiple times within one iteration.
Browbeat has a script which allows a user to generate a CSV file and also has an option to generate a Google Sheet about individual resource
duration through the Rally json file. To use the script to upload to Google Sheets, a Google Drive service account is required.
The script sends an email to the email id of the user with the Google sheet if the --uploadgooglesheet option is enabled.

To generate only a CSV file and not upload to Google Sheets :

::

    $ source .browbeat-venv/bin/activate && cd utils
    $ python rally_google_sheet_gen.py -c -f <path to directory to write csv file locally>
      -j <path to rally json file>
      -a <space separated list of atomic actions(Eg.: boot_server create_network)>

To only upload to Google Sheets and not generate CSV files :

::
    $ source .browbeat-venv/bin/activate && cd utils
    $ python rally_google_sheet_gen.py
      -j <path to rally json file>
      -a <space separated list of atomic actions(Eg.: boot_server create_network)> -g                                                           
      -s <path to google service account json credentials file>
      -e <email id of user> -n <name of google sheet to be created>


To generate a CSV file and upload to Google Sheets :

::
    $ source .browbeat-venv/bin/activate && cd utils
    $ python rally_google_sheet_gen.py -c -f <path to directory to write csv file locally>
      -j <path to rally json file>
      -a <space separated list of atomic actions(Eg.: boot_server create_network)> -g                                                           
      -s <path to google service account json credentials file>
      -e <email id of user> -n <name of google sheet to be created>

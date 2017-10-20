=============================
Developing against Quickstart
=============================

This document helps you with creating a Tripleo Virtual Cloud on your local machine to assist
with developing/testing Browbeat.

Why use Quickstart?
-------------------

Tripleo-Quickstart enables us to have an entire tiny cloud to run Browbeat against.  It gives
you a virtual Undercloud, virtual Overcloud Controller and Computes and other virtual nodes as
well.  This allows you (with understood limitations) to run Browbeat, test commits, or develop
actively with new code without requring a full set of hardware or to run code through CI.

Limitations
-----------

Since everything is virtualized on your local hardware, any performance results are subject to the
limitations of your hardware as well as performance behaving with "noisy neighbors".  This is only
recommended for testing Browbeat and/or gaining familiarity with OpenStack Tripleo Clouds.

Hardware Requirements
---------------------

Memory will most likely be your limitation:

* 16GiB Memory+Swap

  * Undercloud, 1 Controller

* 32GiB Memory is recommended

  * Undercloud, 1 Controller
  * Undercloud, 1 Controller, 1 Compute
  * Undercloud, 3 Controllers

4 physical cpu cores is recommended with at least 50GB of free disk space ideally on an SSD.

Localhost Preparation
---------------------

Ensure that sshd is running on your localhost

.. code-block:: none

  [akrzos@bithead ~]$ sudo systemctl enable sshd
  [akrzos@bithead ~]$ sudo systemctl start sshd

Map 127.0.0.2 to your local host

.. code-block:: none

  [akrzos@bithead ~]$ sudo cat /etc/hosts
  127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4 127.0.0.2
  ::1         localhost localhost.localdomain localhost6 localhost6.localdomain6

Create a Quickstart cloud
-------------------------

Download quickstart.sh
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

  [akrzos@bithead ~]$ curl -O https://raw.githubusercontent.com/openstack/tripleo-quickstart/master/quickstart.sh

Install dependencies
~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

  [akrzos@bithead ~]$ bash quickstart.sh --install-deps

Create Configuration and Nodes YAML Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For this usage of Tripleo-quickstart, there are two configuration files to build a cloud,
quickstart_config.yml and quickstart_nodes.yml configuration file.  Quickstart_config.yml contains
some basic options you may configure for your under/over clouds including ssl, cached image urls,
enabling telemetry, and the networking setup. The nodes configuration file defines the
amount of resources for your virtual overcloud including node count, Three examples are included
here.

quickstart_config.yml

.. code-block:: yaml

  # Allow unsupported distros to deploy QuickStart (Ex. Fedora 24)
  supported_distro_check: false

  # Turn off Undercloud SSL
  undercloud_generate_service_certificate: false

  # Turn off Overcloud SSL
  ssl_overcloud: false

  # Turn off introspection
  step_introspect: false

  # Version of OpenStack (Ex: newton, ocata, pike)
  release: ocata

  #overcloud_as_undercloud: false
  #force_cached_images: true
  #dlrn_hash: current-passed-ci

  # Use cached images when possible
  #undercloud_image_url: http://walkabout.foobar.com/ci-images/ocata/current-passed-ci/undercloud.qcow2
  #ipa_image_url: http://walkabout.foobar.com/ci-images/ocata/current-passed-ci/ironic-python-agent.tar
  #overcloud_image_url: http://walkabout.foobar.com/ci-images/ocata/current-passed-ci/overcloud-full.tar

  # Tell tripleo how we want things done.
  extra_args: >-
    --ntp-server pool.ntp.org

  # This config is extremely resource intensive, so we disable telemetry
  # in order to reduce the overall memory footprint
  # This is not required in newton
  telemetry_args: >-
     {% if release != 'newton' %}
     -e {{ overcloud_templates_path }}/environments/disable-telemetry.yaml
     {% endif %}

  network_isolation: true
  network_isolation_type: 'single-nic-vlans'

  # Network setting on the virthost
  external_network_cidr: 192.168.23.0/24
  networks:
    - name: overcloud
      bridge: brovc
      address: "{{ undercloud_network_cidr|nthhost(2) }}"
      netmask: "{{ undercloud_network_cidr|ipaddr('netmask') }}"

    - name: external
      bridge: brext
      forward_mode: nat
      address: "{{ external_network_cidr|nthhost(1) }}"
      netmask: "{{ external_network_cidr|ipaddr('netmask') }}"
      dhcp_range:
        - "{{ external_network_cidr|nthhost(10) }}"
        - "{{ external_network_cidr|nthhost(50) }}"
      nat_port_range:
        - 1024
        - 65535

  # Below are the networking options you will most likely need to adjust for your local environment
  # some are dervived from other vars and do not need to be adjusted.
  undercloud_external_network_cidr: 172.21.0.0/24
  undercloud_networks:
    external:
      address: "{{ undercloud_external_network_cidr|nthhost(1) }}"
      netmask: "{{ undercloud_external_network_cidr|ipaddr('netmask') }}"
      address6: "{{ undercloud_external_network_cidr6|nthhost(1) }}"
      device_type: ovs
      type: OVSIntPort
      ovs_bridge: br-ctlplane
      ovs_options: '"tag=10"'
      tag: 10

  network_environment_args:
    ControlPlaneSubnetCidr: "{{ undercloud_network_cidr|ipaddr('prefix') }}"
    ControlPlaneDefaultRoute: "{{ undercloud_network_cidr|nthhost(1) }}"
    EC2MetadataIp: "{{ undercloud_network_cidr|nthhost(1) }}"

    ExternalNetCidr: 172.21.0.0/24
    ExternalAllocationPools: [{"start": "172.21.0.10", "end": "172.21.0.100"}]
    ExternalInterfaceDefaultRoute: 172.21.0.1
    NeutronExternalNetworkBridge: "''"

    InternalApiNetCidr: 172.16.0.0/24
    InternalApiAllocationPools: [{"start": "172.16.0.10", "end": "172.16.0.200"}]

    StorageNetCidr: 172.18.0.0/24
    StorageAllocationPools: [{"start": "172.18.0.10", "end": "172.18.0.200"}]

    StorageMgmtNetCidr: 172.19.0.0/24
    StorageMgmtAllocationPools: [{"start": "172.19.0.10", "end": "172.19.0.200"}]

    TenantNetCidr: 172.17.0.0/24
    TenantAllocationPools: [{"start": "172.17.0.10", "end": "172.17.0.250"}]
    DnsServers: [ '{{ external_network_cidr6|nthhost(1) }}' ]

quickstart_nodes.yml - 1 Controller

.. code-block:: yaml

  # Undercloud Virtual Hardware
  undercloud_memory: 8192
  undercloud_vcpu: 2

  # Controller Virtual Hardware
  control_memory: 6144
  control_vcpu: 2

  # Define a single controller node
  overcloud_nodes:
    - name: control_0
      flavor: control
      virtualbmc_port: 6230

  node_count: 1

  deployed_server_overcloud_roles:
    - name: Controller
      hosts: "$(sed -n 1,1p /etc/nodepool/sub_nodes)"

  topology: >-
    --compute-scale 0

quickstart_nodes.yml - 1 Controller, 1 Compute

.. code-block:: yaml

  # Undercloud Virtual Hardware
  undercloud_memory: 8192
  undercloud_vcpu: 2

  # Controller Virtual Hardware
  control_memory: 6144
  control_vcpu: 2

  # Compute Virtual Hardware
  compute_memory: 4096
  compute_vcpu: 1

  overcloud_nodes:
    - name: control_0
      flavor: control
      virtualbmc_port: 6230
    - name: compute_0
      flavor: compute
      virtualbmc_port: 6231

  node_count: 2

  deployed_server_overcloud_roles:
    - name: Controller
      hosts: "$(sed -n 1,1p /etc/nodepool/sub_nodes)"

  topology: >-
    --compute-scale 1
    --control-scale 1

quickstart_nodes.yml - 3 Controllers

.. code-block:: yaml

  # Undercloud Virtual Hardware
  undercloud_memory: 8192
  undercloud_vcpu: 2

  # Controller Virtual Hardware
  control_memory: 6144
  control_vcpu: 1

  # Define a single controller node
  overcloud_nodes:
    - name: control_0
      flavor: control
      virtualbmc_port: 6230
    - name: control_1
      flavor: control
      virtualbmc_port: 6231
    - name: control_2
      flavor: control
      virtualbmc_port: 6232

  node_count: 3

  deployed_server_overcloud_roles:
    - name: Controller
      hosts: "$(sed -n 1,1p /etc/nodepool/sub_nodes)"

  topology: >-
    --compute-scale 0
    --control-scale 3

Run quickstart.sh playbooks

You can change version of OpenStack (Ex. newton, ocata, master) you need by editing the `release`
yaml parameter in quickstart_config.yaml (above).

::

  time bash quickstart.sh -v -c quickstart_config.yml -N quickstart_nodes.yml -I -t all -p quickstart.yml -T all -X 127.0.0.2

::

  time bash quickstart.sh -v -c quickstart_config.yml -N quickstart_nodes.yml -I -t all -p quickstart-extras-undercloud.yml -T none 127.0.0.2

::

  time bash quickstart.sh -v -c quickstart_config.yml -N quickstart_nodes.yml -I -t all -p quickstart-extras-overcloud-prep.yml -T none 127.0.0.2

::

  time bash quickstart.sh -v -c quickstart_config.yml -N quickstart_nodes.yml -I -t all -p quickstart-extras-overcloud.yml -T none 127.0.0.2

If all 4 playbooks completed without errors, you should have a local tripleo quickstart cloud.  In
order to validate, I would recommend ssh-ing into the Undercloud and issuing various openstack cli
commands against the overcloud to verify the health of your quickstart-deployment.

Connecting to your Undercloud/Overcloud from your local machine
---------------------------------------------------------------

Create a vlan10 for external network access

.. code-block:: none

  [root@bithead network-scripts]# cat ifcfg-brovc.10
  DEVICE=brovc.10
  ONBOOT=yes
  HOTPLUG=no
  NM_CONTROLLED=no
  VLAN=yes
  IPADDR=172.21.0.2
  NETMASK=255.255.255.0
  BOOTPROTO=none
  MTU=1500
  [root@bithead network-scripts]# ifup brovc.10

You can now access the overcloud's external/public api endpoints from your local machine and
install Browbeat for benchmarking against it.

Setup Browbeat with Rally against your Quickstart Cloud
-------------------------------------------------------

After you have your Quickstart cloud up and the networking connectivity working, you will want
to run Browbeat against it so you can begin contributing.  Follow the next commands in order to
setup Browbeat with Rally against your local quickstart cloud.

.. code-block:: none

  [akrzos@bithead ~]$ git clone git@github.com:openstack/browbeat.git
  Cloning into 'browbeat'...
  Warning: Permanently added 'github.com,192.30.253.112' (RSA) to the list of known hosts.
  remote: Counting objects: 8567, done.
  remote: Compressing objects: 100% (28/28), done.
  remote: Total 8567 (delta 19), reused 18 (delta 15), pack-reused 8523
  Receiving objects: 100% (8567/8567), 5.52 MiB | 3.44 MiB/s, done.
  Resolving deltas: 100% (4963/4963), done.
  Checking connectivity... done.
  [akrzos@bithead ~]$ cd browbeat/
  [akrzos@bithead browbeat]$ virtualenv .browbeat-venv
  New python executable in /home/akrzos/browbeat/.browbeat-venv/bin/python2
  Also creating executable in /home/akrzos/browbeat/.browbeat-venv/bin/python
  Installing setuptools, pip, wheel...done.
  [akrzos@bithead browbeat]$ virtualenv .rally-venv
  New python executable in /home/akrzos/browbeat/.rally-venv/bin/python2
  Also creating executable in /home/akrzos/browbeat/.rally-venv/bin/python
  Installing setuptools, pip, wheel...done.
  [akrzos@bithead browbeat]$ . .rally-venv/bin/activate
  (.rally-venv) [akrzos@bithead browbeat]$ pip install rally==0.9.1 ansible==2.3.2.0 elasticsearch
  ...(Truncated)
  (.rally-venv) [akrzos@bithead browbeat]$ rally-manage db recreate
  (.rally-venv) [akrzos@bithead browbeat]$ scp -F ~/.quickstart/ssh.config.ansible stack@undercloud:overcloudrc .
  Warning: Permanently added '127.0.0.2' (ECDSA) to the list of known hosts.
  Warning: Permanently added 'undercloud' (ECDSA) to the list of known hosts.
  overcloudrc                                                                        100%  620     0.6KB/s   00:00
  Killed by signal 1.
  (.rally-venv) [akrzos@bithead browbeat]$ . overcloudrc
  (.rally-venv) [akrzos@bithead browbeat]$ rally deployment create --fromenv --name overcloud
  2017-09-21 14:51:41.011 22178 INFO rally.deployment.engine [-] Deployment 41c2e7da-2d30-4e21-acea-6234ec0e73e8 | Starting:  OpenStack cloud deployment.
  2017-09-21 14:51:41.022 22178 INFO rally.deployment.engine [-] Deployment 41c2e7da-2d30-4e21-acea-6234ec0e73e8 | Completed: OpenStack cloud deployment.
  +--------------------------------------+----------------------------+-----------+------------------+--------+
  | uuid                                 | created_at                 | name      | status           | active |
  +--------------------------------------+----------------------------+-----------+------------------+--------+
  | 41c2e7da-2d30-4e21-acea-6234ec0e73e8 | 2017-09-21 18:51:41.006885 | overcloud | deploy->finished |        |
  +--------------------------------------+----------------------------+-----------+------------------+--------+
  Using deployment: 41c2e7da-2d30-4e21-acea-6234ec0e73e8
  ...(Truncated)
  (.rally-venv) [akrzos@bithead browbeat]$ rally deployment list
  +--------------------------------------+----------------------------+-----------+------------------+--------+
  | uuid                                 | created_at                 | name      | status           | active |
  +--------------------------------------+----------------------------+-----------+------------------+--------+
  | 41c2e7da-2d30-4e21-acea-6234ec0e73e8 | 2017-09-21 18:51:41.006885 | overcloud | deploy->finished | *      |
  +--------------------------------------+----------------------------+-----------+------------------+--------+
  (.rally-venv) [akrzos@bithead browbeat]$ deactivate
  [akrzos@bithead browbeat]$ . .browbeat-venv/bin/activate
  (.browbeat-venv) [akrzos@bithead browbeat]$ pip install -Ur requirements.txt
  ...(Truncated)
  (.browbeat-venv) [akrzos@bithead browbeat]$ cp browbeat-config.yaml browbeat-quickstart.yml
  (.browbeat-venv) [akrzos@bithead browbeat]$ vi browbeat-quickstart.yml
  (.browbeat-venv) [akrzos@bithead browbeat]$ ./browbeat.py -s browbeat-quickstart.yml rally
  2017-09-21 18:55:51,231 - browbeat.tools -    INFO - Validating the configuration file passed by the user
  2017-09-21 18:55:51,289 - browbeat.tools -    INFO - Validation successful
  2017-09-21 18:55:51,289 - browbeat -    INFO - Browbeat test suite kicked off
  2017-09-21 18:55:51,289 - browbeat -    INFO - Browbeat UUID: 970b8bee-72ec-489e-a7b4-d70e0ee4fb42
  2017-09-21 18:55:51,289 - browbeat -    INFO - Running workload(s): rally
  2017-09-21 18:55:51,290 - browbeat.rally -    INFO - Starting Rally workloads
  2017-09-21 18:55:51,290 - browbeat.rally -    INFO - Benchmark: authenticate
  2017-09-21 18:55:51,290 - browbeat.rally -    INFO - Running Scenario: authentic-keystone
  2017-09-21 18:56:17,812 - browbeat.rally -    INFO - Generating Rally HTML for task_id : 66c81969-daae-4e06-8124-8a73bee7084c
  2017-09-21 18:56:19,488 - browbeat.rally -    INFO - Current number of Rally scenarios executed:1
  2017-09-21 18:56:19,488 - browbeat.rally -    INFO - Current number of Rally tests executed:1
  2017-09-21 18:56:19,489 - browbeat.rally -    INFO - Current number of Rally tests passed:1
  2017-09-21 18:56:19,489 - browbeat.rally -    INFO - Current number of Rally test failures:0
  2017-09-21 18:56:20,370 - browbeat -    INFO - Saved browbeat result summary to results/20170921-185551.report
  2017-09-21 18:56:20,370 - browbeat.workloadbase -    INFO - Total scenarios executed:1
  2017-09-21 18:56:20,371 - browbeat.workloadbase -    INFO - Total tests executed:1
  2017-09-21 18:56:20,371 - browbeat.workloadbase -    INFO - Total tests passed:1
  2017-09-21 18:56:20,371 - browbeat.workloadbase -    INFO - Total tests failed:0
  2017-09-21 18:56:20,371 - browbeat -    INFO - Browbeat finished successfully, UUID: 970b8bee-72ec-489e-a7b4-d70e0ee4fb42
  (.browbeat-venv) [akrzos@bithead browbeat]$

Edit your browbeat-config and validate the following:

* Elastic Indexing configuration
* Scenarios you want to run are setup and set to a low times/concurrency

Troubleshooting
---------------

View Undercloud and Overcloud Instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

  [root@bithead ~]# sudo su - stack -c 'virsh list --all'
   Id    Name                           State
  ----------------------------------------------------
   1     undercloud                     running
   3     compute_0                      running
   4     control_0                      running

Accessing Virtual Baremetal Nodes consoles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

  [root@bithead ~]# sudo su - stack -c 'virsh -c qemu:///session console undercloud'
  Connected to domain undercloud
  Escape character is ^]

  Red Hat Enterprise Linux Server 7.3 (Maipo)
  Kernel 3.10.0-514.26.2.el7.x86_64 on an x86_64

  undercloud login:

Get to Undercloud via ssh
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

  [akrzos@bithead ~]$ ssh -F ~/.quickstart/ssh.config.ansible undercloud
  Warning: Permanently added '127.0.0.2' (ECDSA) to the list of known hosts.
  Warning: Permanently added 'undercloud' (ECDSA) to the list of known hosts.
  Last login: Tue Sep 19 13:25:33 2017 from gateway
  [stack@undercloud ~]$

Get to Overcloud nodes via ssh
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: none

  [akrzos@bithead ~]$ ssh -F ~/.quickstart/ssh.config.ansible overcloud-controller-0
  Warning: Permanently added '127.0.0.2' (ECDSA) to the list of known hosts.
  Warning: Permanently added 'undercloud' (ECDSA) to the list of known hosts.
  Last login: Tue Sep 19 13:25:33 2017 from gateway
  [heat-admin@overcloud-controller-0 ~]$

Other gotchas
~~~~~~~~~~~~~

Make sure your / partition does not fill up with cached images as they can take a large amount
of space

.. code-block:: none

  [root@bithead ~]# df -h /var/cache/tripleo-quickstart/
  Filesystem                           Size  Used Avail Use% Mounted on
  /dev/mapper/fedora_dhcp23--196-root   50G   40G  6.9G  86% /
  [root@bithead ~]# du -sh /var/cache/tripleo-quickstart/
  5.4G	/var/cache/tripleo-quickstart/

Further Documentation
~~~~~~~~~~~~~~~~~~~~~

`Tripleo Quickstart docs <https://docs.openstack.org/tripleo-quickstart/latest/>`_

============
Installation
============

Browbeat is currently installed via an ansible playbook.  In a Tripleo
environment it can be installed directly on the Undercloud or a separate
machine.  The installation can be run from either your local machine or
directly on the machine you want Browbeat installed on.

Install Browbeat on Undercloud
------------------------------

This is usually the easiest installation due to many requirements are satisfied
on the Undercloud. In some cases it may not be desired to install Browbeat on
the Undercloud (Ex. Limited Resource requirements or Non-Tripleo installed
cloud)

Requirements
~~~~~~~~~~~~

Hardware

* Undercloud Machine (Baremetal or Virtual Machine)

Networking

* Access to Public API endpoints
* Access to Keystone Admin Endpoint

.. note::  For tripleo, public API endpoints are located on the External
  Network by default. The Keystone Admin Endpoint is deployed on the ctlplane
  network by default.  These networking requirements should be validated before
  attempting an installation.

On the Undercloud
~~~~~~~~~~~~~~~~~

::

  $ ssh undercloud-root
  [root@undercloud ~]# su - stack
  [stack@undercloud ~]$ git clone https://github.com/openstack/browbeat.git
  [stack@undercloud ~]$ source stackrc
  [stack@undercloud ~]$ cd browbeat/ansible
  [stack@undercloud ansible]$ ./generate_tripleo_inventory.sh -l
  [stack@undercloud ansible]$ sudo easy_install pip
  [stack@undercloud ansible]$ sudo pip install ansible
  [stack@undercloud ansible]$ vi install/group_vars/all.yml # Make sure to edit the dns_server to the correct ip address
  [stack@undercloud ansible]$ ansible-playbook -i hosts.yml install/browbeat.yml
  [stack@undercloud ansible]$ ansible-playbook -i hosts.yml install/shaker_build.yml

.. note:: Your default network might not work for you depending on your
   underlay/overlay network setup. In such cases, user needs to create
   appropriate networks for instances to allow them to reach the
   internet. Some useful documentation can be found at:
   https://access.redhat.com/documentation/en/red-hat-openstack-platform/11/single/networking-guide/

(Optional) Clone e2e-benchmarking repository and deploy benchmark-operator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
e2e-benchmarking is a repository that is used to run workloads to stress an Openshift
cluster, and is needed to run shift-on-stack workloads in Browbeat.

To enable the e2e-benchmarking repository to be cloned and benchmark-operator to be deployed,
set install_e2e_benchmarking: true in ansible/install/group_vars/all.yml.
After that, add the kubeconfig paths of all your Openshift clusters in the ansible/kubeconfig_paths
file. Move the default kubeconfig file(/home/stack/.kube/config) to another location so that it isn't
used for all Openshift clusters. After that, run the command mentioned below.

  [stack@undercloud ansible]$ ansible-playbook -i hosts.yml install/browbeat.yml

(Optional) Install Browbeat instance workloads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Browbeat instance workloads are orchestrated Rally plugins that ship with Browbeat.
We currently support a handful of workloads

- Pbench-Uperf - Networking throughput / RR test
- Linpack - Microbenchmark for CPU load

To enable installation of the Browbeat workloads set install_browbeat_workloads: true
in ansible/install/group_vars/all.yml.

To build the custom images for workloads set enabled: true
in ansible/install/group_vars/all.yml.

Example:
        browbeat_workloads:
          sysbench:
            name: browbeat-sysbench
            src: sysbench-user.file
            dest: "{{ browbeat_path }}/sysbench-user.file"
            image: centos7
            enabled: true

It is also required to provide the neutron network id of a private network which
has external access. To set this, edit ansible/install/group_vars/all.yml and
provide the network id for the browbeat_network:

This work can either be done prior to installation of Browbeat, or after Browbeat
has been installed. To skip directly to this task execute:

::

    $ ansible-playbook -i hosts install/browbeat.yml --start-at-task "Check browbeat_network"



(Optional) Install Collectd
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``collectd_container`` is set to true if running on OpenStack version Stein or later. The containerized collectd can also work with Queens release but it is not recommended.

::

  [stack@ospd ansible]$ ansible-playbook -i hosts install/collectd.yml

(Optional) Install Rsyslogd logging with aggregation (not maintained)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First configure the values rsyslog values and elasticsearch parameters in
`ansible/install/group_vars/all.yml`. If you have a large number of hosts
deploying an aggregator using `ansible/install/rsyslog-aggregator.yml`
is strongly suggested. If you have a small scale, change the value
rsyslog_forwarding in `all.yml` to `false`. Once things are configured
to your liking deploy logging on the cloud using the `rsyslog-logging.yml`
playbook.

Firewall configuration for the aggregator is left up to the user. The logging
install playbook will check that the aggregator is up and the port is open if
you deploy with aggregation.

::

  [stack@ospd ansible]$ vim install/group_vars/all.yml
  [stack@ospd ansible]$ ansible-playbook -i hosts install/rsyslog-aggregator.yml
  [stack@ospd ansible]$ ansible-playbook -i hosts install/rsyslog-logging.yml

(Optional) Install Browbeat Grafana dashboards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Browbeat uses Grafyaml to upload dashboards to Grafana. Grafyaml is installed by browbeat
at the location pointed to by the variable `browbeat_venv` in `ansible/install/group_vars/all.yml`.
To upload dashboards, the api key is required which can be generated by following instructions at
http://docs.grafana.org/http_api/auth/#create-api-token

::

  [stack@ospd ansible]$ # update the vars and make sure to update grafana_apikey with value
  [stack@ospd ansible]$ vi install/group_vars/all.yml
  [stack@ospd ansible]$ ansible-playbook -i hosts install/browbeat.yml # if not run before.
  [stack@ospd ansible]$ ansible-playbook -i hosts install/grafana-dashboards.yml

(Optional) Install Browbeat Prometheus/Grafana/Collectd
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::
  [stack@ospd ansible]$ ansible-playbook -i hosts install/grafana-prometheus-dashboards.yml

Make sure grafana-api-key is added in the `install/group_vars/all.yml`

(Optional) Install Browbeat Common Logging through filebeat
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Browbeat can be used to setup common logging on your OpenStack Cluster using Filebeat on the
client side and Elasticsearch on the server side. Set the `cloud_prefix` and `es_ip` in
`install/group_vars/all.yml` before running the playbook to setup common logging for your cloud.

::

  [stack@ospd ansible]$ # update the vars
  [stack@ospd ansible]$ vi install/group_vars/all.yml
  [stack@ospd ansible]$ # install filebeat
  [stack@ospd ansible]$ ansible-playbook -i hosts common_logging/install_logging.yml
  [stack@ospd ansible]$ # install and start filebeat
  [stack@ospd ansible]$ ansible-playbook -i hosts common_logging/install_logging.yml -e "start_filebeat=True"

Not mantained (Pre-Pike): Run Overcloud checks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  [stack@ospd ansible]$ ansible-playbook -i hosts check/site.yml

Your Overcloud check output is located in results/bug_report.log

Install Browbeat from your local machine
----------------------------------------

This installs Browbeat onto your Undercloud but the playbook is run from your
local machine rather than directly on the Undercloud machine.

From your local machine
~~~~~~~~~~~~~~~~~~~~~~~

::

  $ ssh-copy-id stack@<undercloud-ip>
  $ git clone https://github.com/openstack/browbeat.git
  $ cd browbeat/ansible
  $ ./generate_tripleo_hostfile.sh -t <undercloud-ip>
  $ vi install/group_vars/all.yml # Review and edit configuration items
  $ ansible-playbook -i hosts install/browbeat.yml
  $ ansible-playbook -i hosts install/shaker_build.yml


.. note:: Your default network might not work for you depending on your
   underlay/overlay network setup. In such cases, user needs to create
   appropriate networks for instances to allow them to reach the
   internet. Some useful documentation can be found at:
   https://access.redhat.com/documentation/en-us/red_hat_openstack_platform/13/html/networking_guide/

(Optional) Install collectd
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  $ ansible-playbook -i hosts install/collectd-openstack.yml

(Optional) Install Browbeat Grafana dashboards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Browbeat uses Grafyaml to upload dashboards to Grafana. Grafyaml is installed by browbeat
at the location pointed to by the variable `browbeat_venv` in `ansible/install/group_vars/all.yml`.
So, you need to first run the browbeat install playbook `ansible/install/browbeat.yml` before running
the below playbook.

::

  $ ansible-playbook -i hosts install/grafana-dashboards.yml

Install/Setup Browbeat Machine
------------------------------

This setup is used when running Browbeat on a separate machine than the
Undercloud. Using this method, you can create multiple users on the machine
and each user can be pointed at a different cloud or the same cloud.

Requirements
~~~~~~~~~~~~

Hardware

* Baremetal or Virtual Machine

Networking

* Access to Public API endpoints
* Access to Keystone Admin Endpoint

RPM

* epel-release
* ansible
* git

OpenStack

* overcloudrc file placed in browbeat user home directory

.. note::  For tripleo, public API endpoints are located on the External
  Network by default. The Keystone Admin Endpoint is deployed on the ctlplane
  network by default.  These networking requirements should be validated before
  attempting an installation.

Preparing the Machine (CentOS 7)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Install Machine either from Image, ISO, or PXE
2. Check for Required Network Connectivity

Determine Overcloud Keystone endpoints

::

  [stack@undercloud-1 ~]$ . overcloudrc
  [stack@undercloud-1 ~]$ openstack catalog show identity
  +-----------+----------------------------------------+
  | Field     | Value                                  |
  +-----------+----------------------------------------+
  | endpoints | regionOne                              |
  |           |   publicURL: http://172.21.0.10:5000   |
  |           |   internalURL: http://172.16.0.16:5000 |
  |           |   adminURL: http://192.168.24.61:35357 |
  |           |                                        |
  | name      | keystone                               |
  | type      | identity                               |
  +-----------+----------------------------------------+

Check network connectivity

::

  $ ssh root@browbeatvm
  [root@browbeatvm ~]$ # Ping Keystone Admin API IP Address
  [root@browbeatvm ~]# ping -c 2 192.168.24.61
  PING 192.168.24.61 (192.168.24.61) 56(84) bytes of data.
  64 bytes from 192.168.24.61: icmp_seq=1 ttl=64 time=1.60 ms
  64 bytes from 192.168.24.61: icmp_seq=2 ttl=64 time=0.312 ms

  --- 192.168.24.61 ping statistics ---
  2 packets transmitted, 2 received, 0% packet loss, time 1001ms
  rtt min/avg/max/mdev = 0.312/0.957/1.603/0.646 ms
  [root@browbeatvm ~]$ # Ping Keystone Public API IP Address
  [root@browbeatvm ~]# ping -c 2 172.21.0.10
  PING 172.21.0.10 (172.21.0.10) 56(84) bytes of data.
  64 bytes from 172.21.0.10: icmp_seq=1 ttl=64 time=0.947 ms
  64 bytes from 172.21.0.10: icmp_seq=2 ttl=64 time=0.304 ms

  --- 172.21.0.10 ping statistics ---
  2 packets transmitted, 2 received, 0% packet loss, time 1001ms
  rtt min/avg/max/mdev = 0.304/0.625/0.947/0.322 ms

3. Create user for Browbeat and generate SSH key

::

  [root@browbeatvm ~]# useradd browbeat1
  [root@browbeatvm ~]# passwd browbeat1
  Changing password for user browbeat1.
  New password:
  Retype new password:
  passwd: all authentication tokens updated successfully.
  [root@browbeatvm ~]# echo "browbeat1 ALL=(root) NOPASSWD:ALL" | tee -a /etc/sudoers.d/browbeat1; chmod 0440 /etc/sudoers.d/browbeat1
  browbeat1 ALL=(root) NOPASSWD:ALL
  [root@browbeatvm ~]# su - browbeat1
  [browbeat1@browbeatvm ~]$ ssh-keygen
  Generating public/private rsa key pair.
  Enter file in which to save the key (/home/browbeat1/.ssh/id_rsa):
  Enter passphrase (empty for no passphrase):
  Enter same passphrase again:
  Your identification has been saved in /home/browbeat1/.ssh/id_rsa.
  Your public key has been saved in /home/browbeat1/.ssh/id_rsa.pub.
  The key fingerprint is:
  c2:b2:f0:cd:ef:d2:2b:a8:9a:5a:bb:ca:ce:c1:8c:3b browbeat1@browbeatvm
  The key's randomart image is:
  +--[ RSA 2048]----+
  |                 |
  |                 |
  |                 |
  |     .           |
  |  . . o S        |
  |+  o = .         |
  |.+. o.o.         |
  |E+... o..        |
  |OB+o   ++.       |
  +-----------------+


4. Enable passwordless SSH into localhost and Undercloud then copy overcloudrc over to Browbeat VM

::

  [browbeat1@browbeatvm ansible]$ ssh-copy-id browbeat1@localhost
  /bin/ssh-copy-id: INFO: attempting to log in with the new key(s), to filter out any that are already installed
  /bin/ssh-copy-id: INFO: 1 key(s) remain to be installed -- if you are prompted now it is to install the new keys
  browbeat1@localhost's password:

  Number of key(s) added: 1

  Now try logging into the machine, with:   "ssh 'browbeat1@localhost'"
  and check to make sure that only the key(s) you wanted were added.

  [browbeat1@browbeatvm ~]$ ssh-copy-id stack@undercloud-1
  The authenticity of host 'undercloud-1 (undercloud-1)' can't be established.
  ECDSA key fingerprint is fa:3a:02:e8:8e:92:4d:a7:9c:90:68:6a:c2:eb:fe:e1.
  Are you sure you want to continue connecting (yes/no)? yes
  /bin/ssh-copy-id: INFO: attempting to log in with the new key(s), to filter out any that are already installed
  /bin/ssh-copy-id: INFO: 1 key(s) remain to be installed -- if you are prompted now it is to install the new keys
  stack@undercloud-1's password:

  Number of key(s) added: 1

  Now try logging into the machine, with:   "ssh 'stack@undercloud-1'"
  and check to make sure that only the key(s) you wanted were added.

  [browbeat1@browbeatvm ~]$ scp stack@undercloud-1:/home/stack/overcloudrc .
  overcloudrc                               100%  553     0.5KB/s   00:00

.. note::  In SSL environments, you must copy the certificate over and
  check that the "OS_CA_CERT" variable is set correctly to the copied
  certificate location

5. Install RPM requirements

::

  [browbeat1@browbeatvm ~]$ sudo yum install -y epel-release
  [browbeat1@browbeatvm ~]$ sudo yum install -y ansible git

6. Clone Browbeat

::

  [browbeatuser1@browbeat-vm ~]$ git clone https://github.com/openstack/browbeat.git
  Cloning into 'browbeat'...
  remote: Counting objects: 7425, done.
  remote: Compressing objects: 100% (15/15), done.
  remote: Total 7425 (delta 14), reused 12 (delta 12), pack-reused 7398
  Receiving objects: 100% (7425/7425), 5.23 MiB | 0 bytes/s, done.
  Resolving deltas: 100% (4280/4280), done.

7. Generate hosts, ssh-config, and retrieve heat-admin-id_rsa.

::

  [browbeat1@browbeatvm ~]$ cd browbeat/ansible/
  [browbeat1@browbeatvm ansible]$ ./generate_tripleo_hostfile.sh -t undercloud-1 --localhost
  ...
  [browbeat1@browbeatvm ansible]$ ls ssh-config hosts heat-admin-id_rsa
  heat-admin-id_rsa  hosts  ssh-config

Note use of "--localhost" to indicate the desire to install browbeat on the
localhost rather than the undercloud.

8. Edit installation variables

::

  [browbeat1@browbeatvm ansible]$ vi install/group_vars/all.yml

In this case, adjust browbeat_user, iptables_file and dns_server.  Each
environment is different and thus your configuration options will vary.

.. note::  If you require a proxy to get outside your network, you must
  configure http_proxy, https_proxy, no_proxy variables in the proxy_env
  dictionary in install/group_vars/all.yml

9. Run Browbeat install playbook

::

  [browbeat1@browbeatvm ansible]$ ansible-playbook -i hosts install/browbeat.yml

10. Setup browbeat-config.yaml and test run Rally against cloud

::

  [browbeat1@browbeatvm ansible]$ cd ..
  [browbeat1@browbeatvm browbeat]$ vi browbeat-config.yaml
  [browbeat1@browbeatvm browbeat]$ . .browbeat-venv/bin/activate
  (browbeat-venv) [browbeat1@browbeatvm browbeat]$ python browbeat.py rally

11. Build Shaker image

::

  [browbeatuser1@browbeat-vm ~]$ ansible-playbook -i hosts install/shaker_build.yml

.. note:: Your default network might not work for you depending on your
   underlay/overlay network setup. In such cases, user needs to create
   appropriate networks for instances to allow them to reach the
   internet. Some useful documentation can be found at:
   https://access.redhat.com/documentation/en/red-hat-openstack-platform/11/single/networking-guide/

(Optional) Install collectd
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  [browbeatuser1@browbeat-vm ~]$ ansible-playbook -i hosts install/collectd-openstack.yml

(Optional) Install Browbeat Grafana dashboards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Browbeat uses Grafyaml to upload dashboards to Grafana. Grafyaml is installed by browbeat
at the location pointed to by the variable `browbeat_venv` in `ansible/install/group_vars/all.yml`.
So, you need to first run the browbeat install playbook `ansible/install/browbeat.yml` before running
the below playbook.

::

  [browbeatuser1@browbeat-vm ~]$ ansible-playbook -i hosts install/grafana-dashboards.yml


Considerations for additional Browbeat Installs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If it is desired to run Browbeat against multiple clouds from the same machine.
It is recommended to create a second user (Ex. browbeat2) and repeat above
instructions.  In order to expose the second user's Browbeat results via httpd,
change the port (Variable browbeat_results_port) and thus each user's results
will be available via http on different ports.

.. note::  Keep in mind that running multiple sets of control plane workloads
  from multiple Browbeat users at the same time will introduce variation into
  resulting performance data if the machine on which Browbeat is installed is
  resource constrained.

Using Keystone Public Endpoint
------------------------------

If your Browbeat installation can not reach the Keystone Admin API endpoint due
to the networking, you can use Keystone V3 options.  In your overcloudrc or rc
file you can add the following environment variables.

::

  export OS_IDENTITY_API_VERSION=3
  export OS_INTERFACE=public

Uploading Images to the overcloud
---------------------------------

Browbeat by default uploads CentOS and CirrOS images to the cloud for use in
Rally and other workloads. It is recommended to upload RAW images if using ceph
and hence the convert_to_raw  variable must be set to true as shown below in
ansible/install/group_vars/all.yml. The default is false.

::

  images:
    centos7:
      name: centos7
      url: http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
      type: qcow2
      convert_to_raw: true

==================================
Additional Components Installation
==================================

Install Monitoring Host (Carbon/Graphite/Grafana)
-------------------------------------------------

A monitoring host exposes System and Application performance metrics to the
Browbeat user via Grafana.  It helps expose what may be causing your bottleneck
when you encounter a performance issue.

Prerequisites
~~~~~~~~~~~~~

Hardware

* Baremetal or Virtual Machine
* SSD storage

Operating System

* RHEL 7
* CentOS 7

Repos

* Red Hat Enterprise Linux 7Server - x86_64 - Server
* Red Hat Enterprise Linux 7Server - x86_64 - Server Optional

RPM

* epel-release
* ansible
* git

Installation
~~~~~~~~~~~~

1. Deploy machine (RHEL7 is used in this example)
2. Install RPMS

::

  [root@dhcp23-93 ~]# yum install -y https://download.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
  ...
  [root@dhcp23-93 ~]# yum install -y ansible git

3. Clone Browbeat

::

  [root@dhcp23-93 ~]# git clone https://github.com/openstack/browbeat.git
  Cloning into 'browbeat'...
  remote: Counting objects: 7533, done.
  remote: Compressing objects: 100% (38/38), done.
  remote: Total 7533 (delta 30), reused 36 (delta 23), pack-reused 7469
  Receiving objects: 100% (7533/7533), 5.26 MiB | 5.79 MiB/s, done.
  Resolving deltas: 100% (4330/4330), done.

4. Add a hosts file into ansible directory

::

  [root@dhcp23-93 ~]# cd browbeat/ansible/
  [root@dhcp23-93 ansible]# vi hosts

Content of hosts file should be following

::

  [graphite]
  localhost

  [grafana]
  localhost

5. Setup SSH config, SSH key and exchange for Ansible

::

  [root@dhcp23-93 ansible]# touch ssh-config
  [root@dhcp23-93 ansible]# ssh-keygen
  Generating public/private rsa key pair.
  ...
  [root@dhcp23-93 ansible]# ssh-copy-id root@localhost
  ...

6. Edit install variables

::

  [root@dhcp23-93 ansible]# vi install/group_vars/all.yml

Depending on the environment you may need to edit more than just the following
variables - graphite_host and grafana_host

.. note::  If you require a proxy to get outside your network, you must
  configure http_proxy, https_proxy, no_proxy variables in the proxy_env
  dictionary in install/group_vars/all.yml

7. Install Carbon and Graphite via Ansible playbook

::

  [root@dhcp23-93 ansible]# ansible-playbook -i hosts install/graphite.yml
  ...

8. Install Grafana via Ansible playbook

::

  [root@dhcp23-93 ansible]# ansible-playbook -i hosts install/grafana.yml
  ...

9. Install Grafana dashboards via Ansible playbook

::

  [root@dhcp23-93 ansible]# ansible-playbook -i hosts install/grafana-dashboards.yml -e 'cloud_dashboards=false'
  ...

10. (Optional) Monitor the Monitor Host

::

  [root@dhcp23-93 ansible]# ansible-playbook -i hosts install/collectd-generic.yml --tags graphite
  ...

Now navigate to http://monitoring-host-address:3000 to verify Grafana is
installed, the Graphite data source exists and custom dashboards are uploaded.

You can now point other clouds at this host in order to view System and
Application performance metrics.  Depending on the number of clouds and
machines pointed at your monitoring server, you may need to add more disk IO
capacity, disk storage or carbon-cache+carbon-relay processes depending
entirely on the number of metrics and your environments capacity.  There is a
Graphite dashboard included and it is recommended to install collectd on your
monitoring host such that you can see if you hit resource issues with your
monitoring host.

(Optional) Install Kibana Visualizations
----------------------------------------

1. Update install/group_vars/all.yml (es_ip) to identify your ELK host.
2. Install Kibana Visualizations via Ansible playbook

::

  [root@dhcp23-93 ansible]# ansible-playbook -i hosts install/kibana-visuals.yml
  ...

Now navigate to http://elk-host-address to verify Kibana is
installed and custom visualizations are uploaded.

Table of Contents
=================

-  `Browbeat <#browbeat>`__
-  `Before running browbeat <#before-running-browbeat>`__
-  `How to run Browbeat? <#how-to-run-browbeat>`__
-  `What is necessary? <#what-is-necessary>`__
-  `Detailed Install, Check and Run <#detailed-install-check-and-run>`__
-  `Install Browbeat from your local
   machine <#install-browbeat-from-your-local-machine>`__

   -  `From your local machine <#from-your-local-machine>`__
   -  `(Optional) Install collectd <#optional-install-collectd>`__
   -  `(Optional) Install collectd->graphite
      dashboards <#optional-install-collectd-graphite-dashboards>`__
   -  `(Optional) Install connmon <#optional-install-connmon>`__
   -  `Run Overcloud checks <#run-overcloud-checks>`__
   -  `Run performance stress tests through browbeat on the
      undercloud <#run-performance-stress-tests-through-browbeat-on-the-undercloud>`__

-  `Install Browbeat directly on
   undercloud <#install-browbeat-directly-on-undercloud>`__

   -  `From your undercloud <#from-your-undercloud>`__
   -  `(Optional) Install collectd <#optional-install-collectd>`__
   -  `(Optional) Install collectd->graphite
      dashboards <#optional-install-collectd-graphite-dashboards>`__
   -  `(Optional) Install connmon <#optional-install-connmon>`__
   -  `Run Overcloud checks <#run-overcloud-checks>`__
   -  `Run performance stress tests through
      browbeat <#run-performance-stress-tests-through-browbeat>`__

-  `Running PerfKitBenchmarker <#running-perfkitbenchmarker>`__
-  `Contributing <#contributing>`__
-  `Links and Resources <#resources>`__

Browbeat
========

This started as a project to help determine the number of database
connections a given OpenStack deployment uses via stress tests. It has
since grown into a set of Ansible playbooks to help check deployments
for known issues, install tools, run performance stress workloads and
change parameters of the overcloud.

Before running browbeat
=======================

-  Execute the ansible/gen_hostfile.sh script (builds the ssh config)
-  Configure browbeat-config.yaml to match your tests

How to run Browbeat Stress Tests?
=================================

On the Undercloud host, as the Stack user jump into the browbeat venv
and you simply run:

::

    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py --help

However, the playbook required to install browbeat and its
dependencies(Rally, Shaker, Perfkit) needs to be run before this.
DEtailed install and run instructions are presented in a section below.

What is necessary?
==================

-  TripleO
-  Why? We use passwordless ssh to reach each controller instance and
   compute instance.
-  Ansible
-  Why? We started with using bash to make changes to the Overcloud,
   creating complex sed/awks that we get for free with Ansible (for the
   most part). Other monitoring and stress test tools are installed by
   the respective playbooks when run.

If you prefer to not use Ansible, the older versions (no longer
maintained) of the browbeat.sh can be found in a older commit.

Detailed Install, Check and Run
===============================

Installing Browbeat and running the Overcloud checks can be performed
either from your local machine or from the undercloud. The local machine
install/check assumes you have ansible installed already.

Install Browbeat from your local machine
----------------------------------------

From your local machine
~~~~~~~~~~~~~~~~~~~~~~~

::

    $ ssh-copy-id stack@<undercloud-ip>
    $ git clone https://github.com/openstack/browbeat.git
    $ cd browbeat/ansible
    $ ./gen_hostfile.sh <undercloud-ip> ~/.ssh/config
    $ vi install/group_vars/all.yml # Make sure to edit the dns_server to the correct ip address
    $ ansible-playbook -i hosts install/browbeat.yml
    $ vi install/group_vars/all.yml # Edit browbeat network settings
    $ ansible-playbook -i hosts install/browbeat_network.yml
    $ ansible-playbook -i hosts install/shaker_build.yml

(Optional) Install collectd
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ ansible-playbook -i hosts install/collectd-openstack.yml

(Optional) Install collectd->graphite dashboards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ ansible-playbook -i hosts install/dashboards-openstack.yml

(Optional) Install connmon
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ ansible-playbook -i hosts install/connmon.yml

Run Overcloud checks
~~~~~~~~~~~~~~~~~~~~

::

    $ ansible-playbook -i hosts check/site.yml

Your Overcloud check output is located in check/bug_report.log

NOTE: It is strongly advised to not run the ansible playbooks in a venv.

Run performance stress tests through browbeat on the undercloud:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ ssh undercloud-root
    [root@ospd ~]# su - stack
    [stack@ospd ~]$ screen -S browbeat
    [stack@ospd ~]$ . browbeat-venv/bin/activate
    (browbeat-venv)[stack@ospd ~]$ cd browbeat/
    (browbeat-venv)[stack@ospd browbeat]$ vi browbeat-config.yaml # Edit browbeat-config.yaml to control how many stress tests are run.
    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py <workload> #perfkit, rally, shaker or "all"

Install Browbeat directly on undercloud
---------------------------------------

From your undercloud
~~~~~~~~~~~~~~~~~~~~

::

    $ ssh undercloud-root
    [root@ospd ~]# su - stack
    [stack@ospd ~]$ git clone https://github.com/openstack/browbeat.git
    [stack@ospd ~]$ cd browbeat/ansible
    [stack@ospd ansible]$ ./gen_hostfile.sh localhost ~/.ssh/config
    [stack@ospd ansible]$ sudo easy_install pip
    [stack@ospd ansible]$ sudo pip install ansible
    [stack@ospd ansible]$ vi install/group_vars/all.yml # Make sure to edit the dns_server to the correct ip address
    [stack@ospd ansible]$ ansible-playbook -i hosts install/browbeat.yml
    [stack@ospd ansible]$ vi install/group_vars/all.yml # Edit browbeat network settings
    [stack@ospd ansible]$ ansible-playbook -i hosts install/browbeat_network.yml
    [stack@ospd ansible]$ ansible-playbook -i hosts install/shaker_build.yml

(Optional) Install collectd
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    [stack@ospd ansible]$ ansible-playbook -i hosts install/collectd-openstack.yml

(Optional) Install collectd->graphite dashboards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    [stack@ospd ansible]$ ansible-playbook -i hosts install/dashboards-openstack.yml

(Optional) Install connmon
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    [stack@ospd ansible]$ ansible-playbook -i hosts install/connmon.yml

Run Overcloud checks
~~~~~~~~~~~~~~~~~~~~

::

    [stack@ospd ansible]$ ansible-playbook -i hosts check/site.yml

Your Overcloud check output is located in check/bug_report.log

Run performance stress tests through browbeat
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    [stack@ospd ansible]$ . ../../browbeat-venv/bin/activate
    (browbeat-venv)[stack@ospd ansible]$ cd ..
    (browbeat-venv)[stack@ospd browbeat]$ vi browbeat-config.yaml # Edit browbeat.cfg to control how many stress tests are run.
    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py <workload> #perfkit, rally, shaker or "all"

Running PerfKitBenchmarker
==========================

Work is on-going to utilize PerfKitBenchmarker as a workload provider to
browbeat. Many benchmarks work out of the box with browbeat. You must
ensure that your network is setup correctly to run those benchmarks and
you will need to configure the settings in
ansible/install/group_vars/all.yml for browbeat public/private
networks. Currently tested benchmarks include: aerospike, bonnie++,
cluster_boot, copy_throughput(cp,dd,scp), fio, iperf, mesh_network,
mongodb_ycsb, netperf, object_storage_service, ping, scimark2, and
sysbench_oltp.

To run browbeat's PerfKit Benchmarks, you can start by viewing the
tested benchmark's configuration in conf/browbeat-perfkit-complete.yaml.
You must add them to your specific browbeat config yaml file or
enable/disable the benchmarks you wish to run in the default config file
(browbeat-config.yaml). There are many flags exposed in the
configuration files to tune how those benchmarks run. Additional flags
are exposed in the source code of PerfKitBenchmarker available on the
Google Cloud Github_.

.. _Github: https://github.com/GoogleCloudPlatform/PerfKitBenchmarker

Example running only PerfKitBenchmarker benchmarks with browbeat from
browbeat-config.yaml:

::

    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py  perfkit -s browbeat-config.yaml

Contributing
============

Contributions are most welcome!  You must first create a
Launchpad account and `follow the instructions here <http://docs.openstack.org/infra/manual/developers.html#account-setup>`_
to get started as a new OpenStack contributor.

Once you've signed the contributor license agreement and read through
the above documentation, add your public SSH key under the 'SSH Public Keys'
section of review.openstack.org_.

.. _review.openstack.org: https://review.openstack.org/#/settings/

You can view your public key using:

::

    $ cat ~/.ssh/id_*.pub

Set your username and email for review.openstack.org:

::

    $ git config --global user.email "example@example.com"
    $ git config --global user.name "example"
    $ git config --global --add gitreview.username "example"

Next, Clone the github repository:

::

    $ git clone https://github.com/openstack/browbeat.git

You need to have git-review in order to be able to submit patches using
the gerrit code review system. You can install it using:

::

    $ yum install git-review

To set up your cloned repository to work with OpenStack Gerrit

::

    [user@laptop browbeat]$ git review -s

Make your changes and then commit them. Use:

::

    [user@laptop browbeat]$ git review

If you want to edit an already submitted patch, follow the below series
of steps:

Firstly, go to the browbeat directory. Then,

::

    git review -d Change-Id

Change-Id is the change id number as seen on gerrithub.io.

The above command downloads your patch onto a seperate branch. You might
need to rebase your local branch with remoste master before running the
abovecommand to avoid merge conflicts when you resubmit your edited
patch. To avoid this, Go back to a "safe" commit using

::

    $git reset --hard commit-number

Then,

::

    $ git fetch origin

::

    $ git rebase origin/master

Make the changes on the branch that was setup by using the git review -d
(the name of the branch is along the lines of
review/username/branch_name/patchsetnumber).

Add the files to git and commit your changes using,

::

    $ git commit --amend

You can edit your commit message as well in the prompt shown upon
executing above command.

Finally, push the patch for review using,

::

    $ git review

Resources
=========

* `Blog <https://browbeatproject.org>`_
* `Twitter <https://twitter.com/browbeatproject>`_
* `Code Review <https://review.openstack.org/#/q/project:openstack/browbeat>`_
* `Git Web <https://review.openstack.org/gitweb?p=openstack/browbeat.git;a=summary>`_
* `IRC <http://webchat.freenode.net/?nick=browbeat_user&channels=openstack-browbeat>`_ -- **#openstack-browbeat** (irc.freenode.net)


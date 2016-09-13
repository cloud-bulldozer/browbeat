Table of Contents
=================

-  `Browbeat <#browbeat>`__
-  `Before running Browbeat <#before-running-browbeat>`__
-  `How to run Browbeat Stress Tests <#how-to-run-browbeat-stress-tests>`__
-  `What is necessary <#what-is-necessary>`__
-  `Detailed Install, Check and Run <#detailed-install-check-and-run>`__
-  `Install Browbeat from your local
   machine <#install-browbeat-from-your-local-machine>`__

   -  `From your local machine <#from-your-local-machine>`__
   -  `(Optional) Install collectd <#optional-install-collectd>`__
   -  `(Optional) Install collectd->graphite
      dashboards <#optional-install-collectd-graphite-dashboards>`__
   -  `(Optional) Install connmon <#optional-install-connmon>`__
   -  `Run Overcloud checks <#run-overcloud-checks>`__
   -  `Run performance stress tests through Browbeat on the
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
      Browbeat <#run-performance-stress-tests-through-browbeat>`__

-  `Running PerfKitBenchmarker <#running-perfkitbenchmarker>`__
-  `Working with Multiple Clouds <#working-with-multiple-clouds>`__
-  `Contributing <#contributing>`__

   -  `Adding Functionality <#adding-functionality>`__

-  `Links and Resources <#resources>`__

Browbeat
========

This started as a project to help determine the number of database
connections a given OpenStack deployment uses via stress tests. It has
since grown into a set of Ansible playbooks to help check deployments
for known issues, install tools, run performance stress workloads and
change parameters of the overcloud.

Before running Browbeat
=======================

-  Execute the ansible/generate_tripleo_hostfile.sh script (builds ssh-config file)
-  Configure browbeat-config.yaml to match your tests
-  (Optional) Set your Openstack version metadata in metadata/version.json

Currently Keystone Dashboards only depend on osp_series but may be extended to show
build date in the future, thus build is also provided but not required.  You can
add whatever other version related metadata you would like to metadata/version.json.
Typically, whatever automation you have to produce builds should provide this file.

How to run Browbeat Stress Tests
=================================

On the Undercloud host, as the Stack user jump into the Browbeat venv
and you simply run:

::

    (browbeat-venv)[stack@ospd browbeat]$ ./browbeat.py --help

However, the playbook required to install Browbeat and its
dependencies(Rally, Shaker, Perfkit) needs to be run before this.
DEtailed install and run instructions are presented in a section below.

What is necessary
==================

-  Ansible

   Why? We started with using bash to make changes to the Overcloud,
   creating complex sed/awks that we get for free with Ansible (for the
   most part). Other monitoring and stress test tools are installed by
   the respective playbooks when run.

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
    $ ./generate_tripleo_hostfile.sh <undercloud-ip>
    $ vi install/group_vars/all.yml # Make sure to edit the dns_server to the correct ip address
    $ ansible-playbook -i hosts install/browbeat.yml
    $ vi install/group_vars/all.yml # Edit Browbeat network settings
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

Your Overcloud check output is located in results/bug_report.log

NOTE: It is strongly advised to not run the ansible playbooks in a venv.

Run performance stress tests through Browbeat on the undercloud:
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
    [stack@ospd ansible]$ ./generate_tripleo_hostfile.sh localhost
    [stack@ospd ansible]$ sudo easy_install pip
    [stack@ospd ansible]$ sudo pip install ansible
    [stack@ospd ansible]$ vi install/group_vars/all.yml # Make sure to edit the dns_server to the correct ip address
    [stack@ospd ansible]$ ansible-playbook -i hosts install/browbeat.yml
    [stack@ospd ansible]$ vi install/group_vars/all.yml # Edit Browbeat network settings
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

Your Overcloud check output is located in results/bug_report.log

Run performance stress tests through Browbeat
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

    $ sudo yum install git-review

To set up your cloned repository to work with OpenStack Gerrit

::

    $ git review -s

It's useful to create a branch to do your work, name it something
related to the change you'd like to introduce.

::

    $ cd browbeat
    $ git branch my_special_enhancement
    $ git checkout !$

Make your changes and then commit them using the instructions
below.

::

    $ git add /path/to/files/changed
    $ git commit

Use a descriptive commit title followed by an empty space.
You should type a small justification of what you are
changing and why.

Now you're ready to submit your changes for review:

::

    $ git review


If you want to make another patchset from the same commit you can
use the amend feature after further modification and saving.

::

    $ git add /path/to/files/changed
    $ git commit --amend
    $ git review

If you want to submit a new patchset from a different location
(perhaps on a different machine or computer for example) you can
clone the Browbeat repo again (if it doesn't already exist) and then
use git review against your unique Change-ID:

::

    $ git review -d Change-Id

Change-Id is the change id number as seen in Gerrit and will be
generated after your first successful submission.

The above command downloads your patch onto a separate branch. You might
need to rebase your local branch with remote master before running it to
avoid merge conflicts when you resubmit the edited patch.  To avoid this
go back to a "safe" commit using:

::

    $ git reset --hard commit-number

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

Adding functionality
--------------------

If you are adding new functionality to Browbeat please add testing for that functionality in.

::

    $ ci-scripts/install-and-check.sh

See the README.rst in the ci-scripts folder for more details on the structure of the script and how to add additional tests.

Resources
=========

* `Blog <https://browbeatproject.org>`_
* `Twitter <https://twitter.com/browbeatproject>`_
* `Code Review <https://review.openstack.org/#/q/project:openstack/browbeat>`_
* `Git Web <https://review.openstack.org/gitweb?p=openstack/browbeat.git;a=summary>`_
* `IRC <http://webchat.freenode.net/?nick=browbeat_user&channels=openstack-browbeat>`_ -- **#openstack-browbeat** (irc.freenode.net)

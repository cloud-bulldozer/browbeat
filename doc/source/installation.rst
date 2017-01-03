============
Installation
============

Installing Browbeat and running the Overcloud checks can be performed
either from your local machine or from the undercloud. The local machine
install/check assumes you have ansible installed already.

Before running Browbeat
-----------------------

-  Execute the ansible/generate_tripleo_hostfile.sh script (builds ssh-config file)
-  Configure browbeat-config.yaml to match your tests
-  (Optional) Set your Openstack version metadata in metadata/version.json

Currently Keystone Dashboards only depend on osp_series but may be extended to show
build date in the future, thus build is also provided but not required.  You can
add whatever other version related metadata you would like to metadata/version.json.
Typically, whatever automation you have to produce builds should provide this file.

What is necessary
-----------------

-  Ansible

   Why? We started with using bash to make changes to the Overcloud,
   creating complex sed/awks that we get for free with Ansible (for the
   most part). Other monitoring and stress test tools are installed by
   the respective playbooks when run.

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


Table of Contents
=================

-  `Ansible for Browbeat <#ansible-for-browbeat>`__

   -  `Getting Started <#getting-started>`__
   -  `Ansible Installers <#ansible-installers>`__
   -  `Performance Check <#performance-check>`__
   -  `Performance Tune <#performance-tune>`__
   -  `Adjust your overcloud <#adjust-your-overcloud>`__

Ansible for Browbeat
====================

Currently we support Ansible 1.9.4 within browbeat-venv and Ansible 2.0+ for installation.

Playbooks for:
  * Installing Browbeat, collectd, elk clients, graphite, grafana, and grafana dashboards
  * Check overcloud for performance issues
  * Tune overcloud for performance (Experimental)
  * Adjust number of workers for cinder/keystone/neutron/nova
  * Deploy keystone in eventlet/httpd
  * Adjust keystone token type to UUID/Fernet
  * Adjust neutron l3 agents
  * Adjust nova greenlet_pool_size_max_overflow

Getting Started
---------------

Install your public key into stack's authorized\_keys

::

    # ssh-copy-id stack@<undercloud-ip>

Generate overcloud's inventory file
-----------------------------------

Currently we have two scripts to generate overcloud's inventory file.
    1. generate_tripleo_inventory.sh
    2. generate_tripleo_hostfile.sh

`generate_tripleo_inventory.sh` is the recommended way to generate the overcloud inventory file.
It will use the `tripleo-ansible-inventory` command to generate the inventory file.
It is faster and maintained with tripleo release.

::

    # ./generate_tripleo_inventory.sh <undercloud-ip>

`generate_tripleo_hostfile.sh` is a shell script that will ssh to each machine and prepare the inventory file.
It is deprecated now and very slow, It may get removed in future releases.

::

    # ./generate_tripleo_hostfile.sh <undercloud-ip>

Review the hosts file the script generates.

Ansible Installers
------------------

Install Browbeat
''''''''''''''''

Image upload requires Ansible 2.0

::

    # vi install/group_vars/all.yml

Edit ansible vars file (Installation parameters)

::

    # ansible-playbook -i hosts install/browbeat.yml

Install Collectd Agent (Requires a Graphite Server)
'''''''''''''''''''''''''''''''''''''''''''''''''''

Prior to installing the agent, please review install/group\_vars/all.yml
file to ensure the correct parameters are passed.

::

    # ansible-playbook -i hosts install/collectd.yml

To install collectd on everything other than Openstack machines, view
the `README for collectd-generic <README.collectd-generic.md>`__.

Install Kibana Visuals
''''''''''''''''''''''

Prior to installing the Kibana visuals, please review install/group\_vars/all.yml
file to ensure the correct parameters are passed.

::
    browbeat_path - Point to the browbeat directory, default is /home/stack/browbeat
    es_ip -  Point to the ElasticSerach host, default is blank
    es_kibana_index - Point to the correct Kibana index, default is .kibana

To Install Kibana Visuals

::

    # ansible-playbook -i hosts install/kibana-visuals.yml


Install Generic ELK Clients
'''''''''''''''''''''''''''
Filebeat (official Logstash forwarder) is used here unless you chose the
optional fluentd ``logging_backend`` option in ``install/group_vars/all.yml``.  In this case
a simple rsyslog setup will be implemented.

::

    ansible-playbook -i hosts install/elk-client.yml --extra-vars 'elk_server=X.X.X.X'

The ``elk_server`` variable will be generated after the ELK stack playbook runs,
but it's generally wherever you installed ELK.  If you have an existing ELK
stack you can point new clients to it as well, but you'll want to place a new
client SSL certificate at the location of
``http://{{elk_server}}:{{elk_server_ssl_cert_port}}/filebeat-forwarder.crt``

Install ELK Clients for OpenStack nodes
'''''''''''''''''''''''''''''''''''''''

::

    ansible-playbook -i hosts install/elk-openstack-client.yml --extra-vars 'elk_server=X.X.X.X'

Install graphite service
''''''''''''''''''''''''

When installing graphite, carbon-cache and grafana on a
director/rdo-manager undecloud host, Use the docker playbook instead of
this one.  This playbook is intended for use when you have enough
resources to allocate dedicated systems for the graphing/stats related
services.  Prior to installing grafana, please review
install/group\_vars/all.yml file and your ansible inventory file You
will need to define values for the grafana\_host and graphite\_host IP
addresses here.  Optionally you can change the listening port for
graphite-web.

::

    # ansible-playbook -i hosts install/graphite.yml

Install graphite service as a docker container
''''''''''''''''''''''''''''''''''''''''''''''

Prior to installing graphite as a docker container, please review
install/group\_vars/all.yml file and ensure the docker related settings
will work with your target host. This playbook is ideal when installing
services on director/rdo-manager undercloud host(s).

::

    # ansible-playbook -i hosts install/graphite-docker.yml

Install grafana service
'''''''''''''''''''''''

When installing graphite, carbon-cache and grafana on a
director/rdo-manager undecloud host, Use the docker playbook instead of
this one.  This playbook is intended for use when you have enough
resources to allocate dedicated systems for the graphing/stats related
services.  Prior to installing grafana, please review
install/group\_vars/all.yml file and your ansible inventory file You
will need to define values for the grafana\_host and graphite\_host IP
addresses here.  Optionally you can change the listening port.

::

    # ansible-playbook -i hosts install/grafana.yml

Install grafana service as a docker container
'''''''''''''''''''''''''''''''''''''''''''''

Prior to installing graphite as a docker container, please review
install/group\_vars/all.yml file and ensure the docker related settings
will work with your target host. This playbook is ideal when installing
services on director/rdo-manager undercloud host(s).

::

    # ansible-playbook -i hosts install/grafana-docker.yml

Install Grafana Dashboards (Requires a Grafana Server)
''''''''''''''''''''''''''''''''''''''''''''''''''''''

Review install/group\_vars/all.yml before deploying the grafana
dashboards

::

    # ansible-playbook -i hosts install/dashboards-openstack.yml

Gather Metadata
---------------

Run the gather playbook to gather metadata about how the OpenStack cloud is
currently configured. This playbook writes hardware(No. of CPUs etc),
software(OpenStack Configuration), environment(No. of controllers etc) metadata
files into the metadata directory which are transported to ElasticSearch along
with test results to provide context for the result data.

::

    # ansible-playbook -i hosts gather/site.yml



Performance Check
-----------------

Run the check playbook to identify common performance issues:

::

    # ansible-playbook -i hosts check/site.yml

Performance Tune
----------------

Run the tune playbook to tune your OSPd deployed cloud for performance:

::

    # ansible-playbook -i hosts tune/tune.yml

Adjust your overcloud
---------------------

To modify the number of workers each service is running:

::

    # ansible-playbook -i hosts browbeat/adjustment-workers.yml -e "workers=8"

Openstack services will be running 8 workers per service.

To modify number of workers each service is running and ensure Keystone
is deployed in eventlet:

::

    # ansible-playbook -i hosts browbeat/adjustment-workers.yml -e "workers=8 keystone_deployment=eventlet"

To run Keystone in httpd, change keystone\_deployment to httpd:

::

    # ansible-playbook -i hosts browbeat/adjustment-workers.yml -e "workers=8 keystone_deployment=httpd"

To switch to fernet tokens:

::

    # ansible-playbook -i hosts browbeat/adjustment-keystone-token.yml -e "token_provider=fernet"

To switch to UUID tokens:

::

    # ansible-playbook -i hosts browbeat/adjustment-keystone-token.yml -e "token_provider=uuid"

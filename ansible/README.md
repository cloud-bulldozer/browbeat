Table of Contents
=================

- [Ansible for Browbeat](#ansible-for-browbeat)
    - [Getting Started](#getting-started)
    - [Ansible Installers](#ansible-installers)
    - [Performance Check](#performance-check)
    - [Performance Tune](#performance-tune)
    - [Adjust your overcloud](#adjust-your-overcloud)

# Ansible for Browbeat

Currently we support Ansible 1.9.4 within browbeat-venv and ansible 2.0 for installation.

Playbooks for:
* Installing Browbeat, collectd, connmon, ELK stack and clients, graphite, grafana, and grafana dashboards
* Check overcloud for performance issues
* Tune overcloud for performance (Experimental)
* Adjust number of workers for cinder/keystone/neutron/nova
* Deploy keystone in eventlet/httpd
* Adjust keystone token type to UUID/Fernet
* Adjust neutron l3 agents
* Adjust nova greenlet_pool_size / max_overflow


## Getting Started

Install your public key into stack's authorized_keys
```
# ssh-copy-id stack@<undercloud-ip>
```

Then run generate_tripleo_hosts.sh script to generate your overcloud's hosts file for ansible and generate a "jumpbox" ssh config:
```
# ./generate_tripleo_hostfile.sh <undercloud-ip> ~/.ssh/config
```
*Review the hosts file the script generates.


## Ansible Installers

##### Install Browbeat
Image upload requires Ansible 2.0
```
# vi install/group_vars/all.yml  # Edit ansible vars file (Installation parameters)
# ansible-playbook -i hosts install/browbeat.yml
```

##### Install Collectd Agent (Requires a Graphite Server)
Prior to installing the agent, please review install/group_vars/all.yml file to ensure the correct parameters are passed.
```
# ansible-playbook -i hosts install/collectd-openstack.yml
```
To install collectd on everything other than Openstack machines, view the [README for collectd-generic](README.collectd-generic.md).

##### Install Connmon
Requires Ansible 2.0
```
# ansible-playbook -i hosts install/connmon.yml
```
##### Install Generic ELK Stack
```
ansible-playbook -i hosts install/elk.yml
```
##### Install ELK Stack (on an OpenStack Undercloud)
```
sed -i 's/nginx_kibana_port: 80/nginx_kibana_port: 8888/' install/group_vars/all.yml
sed -i 's/elk_server_ssl_cert_port: 8080/elk_server_ssl_cert_port: 9999/' install/group_vars/all.yml
```
```
ansible-playbook -i hosts install/elk.yml
```
##### Install Generic ELK Clients
```
ansible-playbook -i hosts install/elk-client.yml --extra-vars 'elk_server=X.X.X.X'
```
  - elk_server variable will be generated after the ELK stack playbook runs
#### Install ELK Clients for OpenStack nodes
```
ansible-playbook -i hosts install/elk-openstack-client.yml --extra-vars 'elk_server=X.X.X.X'
```
  - elk_server variable will be generated after the ELK stack playbook runs
##### Install graphite service
```
# ansible-playbook -i hosts install/graphite.yml
```
##### Install graphite service as a docker container
Prior to installing graphite as a docker container, please review install/group_vars/all.yml file and ensure
the docker related settings will work with your target host.
```
# ansible-playbook -i hosts install/graphite-docker.yml
```

##### Install grafana service
Prior to installing grafana, please review install/group_vars/all.yml file and your ansible inventory file
You will need to define values for the grafana_host and graphite_host IP addresses here.
```
# ansible-playbook -i hosts install/grafana.yml
```
##### Install grafana service as a docker container
Prior to installing graphite as a docker container, please review install/group_vars/all.yml file and ensure
the docker related settings will work with your target host.
```
# ansible-playbook -i hosts install/grafana-docker.yml
```

##### Install Grafana Dashboards (Requires a Grafana Server)
Review install/group_vars/all.yml before deploying the grafana dashboards
```
# ansible-playbook -i hosts install/dashboards-openstack.yml
```

## Performance Check

Run the check playbook to identify common performance issues:
```
# ansible-playbook -i hosts check/site.yml
```

## Performance Tune

Run the tune playbook to tune your OSPd deployed cloud for performance:
```
# ansible-playbook -i hosts tune/tune.yml
```

## Adjust your overcloud

To modify the number of workers each service is running:
```
# ansible-playbook -i hosts browbeat/adjustment-workers.yml -e "workers=8"
```
Openstack services will be running 8 workers per service.

To modify number of workers each service is running and ensure Keystone is deployed in eventlet:
```
# ansible-playbook -i hosts browbeat/adjustment-workers.yml -e "workers=8 keystone_deployment=eventlet"
```

To run Keystone in httpd, change keystone_deployment to httpd:
```
# ansible-playbook -i hosts browbeat/adjustment-workers.yml -e "workers=8 keystone_deployment=httpd"
```

To switch to fernet tokens:
```
# ansible-playbook -i hosts browbeat/adjustment-keystone-token.yml -e "token_provider=fernet"
```

To switch to UUID tokens:
```
# ansible-playbook -i hosts browbeat/adjustment-keystone-token.yml -e "token_provider=uuid"
```

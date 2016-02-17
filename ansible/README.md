# Ansible for Browbeat

Currently we only support Ansible 1.9.4.

Playbooks for:
* Install Browbeat
* Install collectd
* Install connmon
* Install grafana dashboards
* Install shaker
* Check overcloud for performance issues
* Tune overcloud for performance (Experimental)
* Adjust number of workers for cinder/keystone/neutron/nova
* Deploy keystone in eventlet/httpd
* Adjust keystone token type to UUID/Fernet
* Adjust neutron l3 agents
* Adjust nova greenlet_pool_size / max_overflow


## To use

Install your public key into stack's authorized_keys
```
# ssh-copy-id stack@<undercloud-ip>
```

Then run gen_hosts.sh script to generate your overcloud's hosts file for ansible and generate a "jumpbox" ssh config:
```
# ./gen_hostfile.sh <undercloud-ip> ~/.ssh/config
```
**Review the hosts file the script generates.


## Ansible Installers:

Install Browbeat
```
# ansible-playbook -i hosts install/browbeat.yml
```

Install Collectd Agent (Requires a Graphite Server)
Prior to installing the agent, please review the install/group_vars/all to ensure the
correct params are passed
```
# ansible-playbook -i hosts install/collectd
```

Install Connmon
```
# ansible-playbook -i hosts install/connmon.yml
```

Install Grafana Dashboards (Requires a Grafana Server)
* Review install/group_vars/all before deploying the grafana dashboards
```
# ansible-playbook -i hosts install/dashboards.yml
```

Install Shaker
```
# ansible-playbook -i hosts install/shaker.yml
```

## Performance Checks:

Run the check playbook to identify common performance issues:
```
# ansible-playbook -i hosts check/site.yml
```

## Performance Tune:

Run the tune playbook to tune your OSPd deployed cloud for performance:
```
# ansible-playbook -i hosts tune/tune.yml
```

## Adjust your overcloud:

To modify the number of workers each service is running:
```
# ansible-playbook -i hosts browbeat/adjustment-workers.yml -e "workers=8"
```
Nova and Keystone will be running 8 workers per service.

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
# ansible-playbook -i hosts browbeat/keystone_token_type.yml -e "token_provider=fernet"
```

To switch to UUID tokens:
```
# ansible-playbook -i hosts browbeat/keystone_token_type.yml -e "token_provider=uuid"
```

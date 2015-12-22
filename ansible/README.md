# Ansible for Browbeat

Playbooks for:
* Install Browbeat
* Install connmon
* Install pbench
* Install shaker
* Check overcloud for performance issues
* Adjust number of workers for nova/keystone
* Deploy keystone in eventlet/httpd
* Switch keystone token type to UUID/Fernet


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

Install Connmon
```
# ansible-playbook -i hosts install/connmon.yml
```

Install Pbench (Requires some knowledge of setting up pbench to have this functionality work completely)
```
# ansible-playbook -i hosts install/pbench.yml
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

## Adjust your overcloud:

To modify the number of workers each service is running:
```
# ansible-playbook -i hosts browbeat/adjustment.yml -e "workers=8"
```
Nova and Keystone will be running 8 workers per service.

To modify number of workers each service is running and ensure Keystone is deployed in eventlet:
```
# ansible-playbook -i hosts browbeat/adjustment.yml -e "workers=8 keystone_deployment=eventlet"
```

To run Keystone in httpd, change keystone_deployment to httpd:
```
# ansible-playbook -i hosts browbeat/adjustment.yml -e "workers=8 keystone_deployment=httpd"
```

To switch to fernet tokens:
```
# ansible-playbook -i hosts browbeat/keystone_token_type.yml -e "token_provider=fernet"
```

To switch to UUID tokens:
```
# ansible-playbook -i hosts browbeat/keystone_token_type.yml -e "token_provider=uuid"
```

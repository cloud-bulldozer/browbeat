# Ansible for Browbeat
Playbooks to modify and performance check the overcloud

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

## Performance Checks:

Run the check playbook to identify common performance issues:

```
# ansible-playbook -i hosts check/site.yml
```

## Ansible to Install connmon/pbench/shaker

```
# ansible-playbook -i hosts install/install.yml -e "pbench=true"
# ansible-playbook -i hosts install/install.yml -e "connmon=true"
# ansible-playbook -i hosts install/install.yml -e "shaker=true"
# ansible-playbook -i hosts install/install.yml -e "pbench=true connmon=true shaker=true"
```

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

To modify the number of workers each service is running, and run keystone in eventlet:

```
# ansible-playbook -i hosts adjustment/site.yml -e "workers=8" -e "deployment=eventlet"
```
Nova and Keystone will be running 8 workers per service.

To run keystone in httpd, change deployment to httpd:

```
# ansible-playbook -i hosts adjustment/site.yml -e "workers=8" -e "deployment=httpd"
```

## Performance Checks:

Run the check playbook to identify common performance issues:

```
# ansible-playbook -i hosts check/site.yml
```


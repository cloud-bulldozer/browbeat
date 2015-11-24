# Ansible for Overcloud changes
Playbook to modify the overcloud.

## To use
Generate the host file for ansible. 

```
# ssh-copy-id stack@<udercloud-ip>
```

Then run our script to generate the hosts file for browbeat.

```
# ./gen_hostfile.sh <undercloud-ip> ~/.ssh/config
```
**Review the host file the script generates.

To modify the number of workers each service is running, set the env variable

```
# export NUM_WORKERS=24
```

Once ansible completes, each serivce will be running 24 workers.

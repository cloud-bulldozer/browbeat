# Ansible for Overcloud changes
Playbook to modify the overcloud.

## To use
To modify the number of workers each service is running, set the env variable

```
# export NUM_WORKERS=24
```

Once ansible completes, each serivce will be running 24 workers.

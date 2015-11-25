# Browbeat
Scripts to help determine number of workers a given OpenStack service needs.

# How to run Browbeat?
On the Red Hat OpenStack Director host, as the Stack user jump into a venv w/ Rally and you simply run:

    ./browbeat.sh

# What is necessary?
* Red Hat OpenStack Director
  * Why? We use the keyless ssh to reach each controller node to maniuplate and check # of workers
* OpenStack Rally
  * Why? We are using Rally to stress the control plane of the env.
* Ansible
  * Why? We started with using bash to make changes to the Overcloud, creating complex sed/awks that we get for free with Ansible (for the most part). If you prefer to not use Ansible, the older versions (no longer maintained) of the browbeat.sh can be found here.


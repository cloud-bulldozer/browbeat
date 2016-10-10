Nova scenarios
==============

We have one required field to make all these Nova scenario's work*:
    net_id - The network ID we should attach all these guests to.

* The Neutron network(s) MUST be set to --shared. If they are not set to --shared, the Rally workload will fail.

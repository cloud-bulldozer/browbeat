=============
Plugins
=============

Rally
~~~~~

Scenario - dynamic-workloads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Dynamic workloads are workloads that aim to simulate a realistic Openstack customer environment, by introducing elements of randomness into the simulation. A list of the different workloads that are part of this Browbeat Rally Plugin is mentioned below.

VM:

- create_delete_servers: Create 'N' VMs(without floating IP), and delete 'M'
  randomly chosen VMs from this list of VMs.
- migrate_servers: Create 'N' VMs(with floating IP), and migrate 'M' randomly
  chosen VMs from this list of VMs across computes, before resizing them.
- swap_floating_ips_between_servers: Swap floating IPs between 2 servers. Ping
  until failure after dissociating floating IPs, before swapping them. Ping until
  success after swapping floating IPs between 2 servers.

Octavia:

- create_loadbalancers: Create 'N' loadbalancers with specified 'M' pools and 'K'
  clients per Loadbalancer.
- delete_loadbalancers: Deletes 'M' loadbalancers randomly from 'N' loadbalancers
- delete_members_random_lb: Deletes 'M' members from a random loadbalancer

Trunk(pod simulation):

- pod_fip_simulation: Simulate pods with floating ips using subports on trunks and
  VMs. Create 'N' trunks and VMs and 'M' subports per trunk/VM. Ping a random subport
  of each trunk/VM from a jumphost.
- add_subports_to_random_trunks: Add 'M' subports to 'N' randomly chosen trunks. This
  is to simulate pods being added to an existing VM.
- delete_subports_from_random_trunks: Delete 'M' subports from 'N' randomly chosen
  trunks. This is is to simulate pods being destroyed.
- swap_floating_ips_between_random_subports: Swap floating IPs between 2 randomly
  chosen subports from 2 trunks.

Provider network:

- provider_netcreate_nova_boot_ping: Creates a provider Network and Boots VM and ping
- provider_net_nova_boot_ping: Boots a VM and ping on random existing provider network
- provider_net_nova_delete: Delete all VM's and provider network

Shift on Stack:

shift_on_stack: Runs specified kube-burner workload through e2e-benchmarking. e2e-benchmarking is a [repository](https://github.com/cloud-bulldozer/e2e-benchmarking.git) that contains scripts to stress Openshift clusters. This workload uses e2e-benchmarking to test Openshift on Openstack.

Context - browbeat_delay
^^^^^^^^^^^^^^^^^^^^^^^^

This context allows a setup and cleanup delay to be introduced into a scenario.

Context - browbeat_persist_network
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This context creates network resources that persist upon completion of a rally run.  It is used in conjunction with the nova_boot_persist_with_network and  nova_boot_persist_with_network_volume plugin scenarios. You can also use `neutron purge` command to purge a project/tenant of neutron network resources.

Scenario - nova_boot_persist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This scenario creates instances without a network that persist upon completion of a rally run.  This scenario is best used for excerising the Telemetry systems within an OpenStack Cloud.  Alternatively, it can be used to put idle instances on a cloud for other workloads to compete for resources.  The scenario is referenced in the Telemetry Browbeat configurations in order to build a "stepped" workload that can be used to analyze Telemetry performance and scalability.

Scenario - nova_boot_persist_with_volume
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This scenario creates instances that have an attached volume and persist upon completion of a rally run. This scenario is best used for excerising the Telemetry systems within an OpenStack Cloud.  It increases the Telemetry workload by creating more resources that the Telemetry services must collect and process metrics over.  Alternatively, it can be used to put idle instances on a cloud for other workloads to compete for resources.  The scenario is referenced in the Telemetry Browbeat configurations in order to build a "stepped" workload that can be used to analyze Telemetry scalability.

Scenario - nova_boot_persist_with_network
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This scenario creates instances that are attached to a network and persist upon completion of a rally run. This scenario is best used for excerising the Telemetry systems within an OpenStack Cloud.  It increases the Telemetry workload by creating more resources that the Telemetry services must collect and process metrics over.  Alternatively, it can be used to put idle instances on a cloud for other workloads to compete for resources.  The scenario is referenced in the Telemetry Browbeat configurations in order to build a "stepped" workload that can be used to analyze Telemetry scalability.

Scenario - nova_boot_persist_with_network_fip
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This scenario creates instances with a nic and associates a floating ip that persist upon completion of a rally run.  It is used as a workload with Telemetry by spawning many instances that have many metrics for the Telemetry subsystem to collect upon.

Scenario - nova_boot_persist_with_network_volume
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This scenario create instances with a nic and a volume that persist upon completion of a rally run.  It is used as a workload with Telemetry by spawning many instances that have many metrics for the Telemetry subsystem to collect upon.

Scenario - nova_boot_persist_with_network_volume_fip
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This scenario creates instances with a nic, a volume and associates a floating ip that persist upon completion of a rally run.  It is used as a workload with Telemetry by spawning many instances that have many metrics for the Telemetry subsystem to collect upon.

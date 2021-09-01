Browbeat Rally Plugin: dynamic-workloads
======================================

Introduction:
-------------
Dynamic workloads are workloads that aim to simulate a realistic Openstack customer
environment, by introducing elements of randomness into the simulation. A list of
the different workloads that are part of this Browbeat Rally Plugin is mentioned
below.

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

How to run the workloads?
-------------------------
- cd to the base directory(browbeat).
- Change enabled to true under the dynamic-workloads and dynamic-workload section of
  browbeat-config.yaml.
- Make changes to parameters under the dynamic-workloads section of browbeat-config.yaml.
- Run ``./browbeat.py rally``

Functions:
----------

Nova Utils:

- log_info: Log information with iteration number
- log_error: Log error with iteration number
- _run_command_with_attempts: Run command over ssh connection with multiple attempts
- _run_command_until_failure: Run command over ssh connection until failure
- assign_ping_fip_from_jumphost: Assign floating IP to port(optional), and ping floating ip from jumphost
- _wait_for_ping_failure: Wait for ping failure to floating IP of server
- _boot_server_with_tag: Boot a server with a tag
- _boot_server_with_fip_and_tag: Boot server prepared for SSH actions, with tag
- _get_servers_by_tag: Retrieve list of servers based on tag
- _get_fip_by_server: Check if server has floating IP, and retrieve it if it does
- show_server: Show server details

Neutron Utils:

- log_info: Log information with iteration number
- log_error: Log error with iteration number
- _create_router: Create neutron router
- dissociate_and_delete_floating_ip: Dissociate and delete floating IP of port
- create_floating_ip_and_associate_to_port: Create and associate floating IP for port
- _create_sec_group_rule: Create rule for security group
- create_sec_group_with_icmp_ssh: Create security group with icmp and ssh rules

Lock Utils:

- acquire_lock: Acquire lock on object
- list_locks: List all locks in database
- release_lock: Release lock on object
- cleanup_locks: Release all locks in database

VM:

- boot_servers: Create 'N' VMs(without floating IP)
- delete_random_servers: Delete 'N' randomly chosen VMs(without floating IP)
- boot_servers_with_fip: Create 'N' VMs with floating IPs.
- _create_router: Create neutron router.
- get_servers_migration_list: Generate list of servers to migrate between computes.
- migrate_servers_with_fip: Migrate servers between computes
- swap_floating_ips_between_servers: Swap floating IPs between 2 servers

Octavia:

- create_loadbalancers: Create 'N' loadbalancers
- delete_loadbalancers: Deletes 'M' loadbalancers randomly from 'N' loadbalancers
- create_clients: Create 'N' clients
- create_listener: Create listener
- create_pool: Create pool
- create_member: Create member
- delete_members_random_lb: Deletes 'M' members from a random loadbalancer
- check_connection: Check the connection of LB
- build_jump_host: Builds Jump host

Trunk:

- add_route_from_vm_to_jumphost: Add route from trunk vm to jumphost via trunk subport
- delete_route_from_vm_to_jumphost: Delete route from trunk vm to jumphost via trunk subport
- get_jumphost_by_trunk: Get jumphost details for a given trunk
- create_subnets_and_subports: Create N subnets and subports
- add_subports_to_trunk_and_vm: Add subports to trunk and create vlan interfaces for subport inside trunk VM
- simulate_subport_connection: Simulate connection from jumphost to random subport of trunk VM
- get_server_by_trunk: Get server details for a given trunk
- pod_fip_simulation: Simulate pods with floating ips using subports on trunks and VMs
- add_subports_to_random_trunks: Add 'N' subports to 'M' randomly chosen trunks
- delete_subports_from_random_trunks: Delete 'N' subports from 'M' randomly chosen trunks
- swap_floating_ips_between_random_subports: Swap floating IPs between 2 randomly chosen subports from 2 randomly chosen trunks

Provider Network:

- provider_netcreate_nova_boot_ping: Creates a provider Network and Boots VM and ping
- provider_net_nova_boot_ping: Boots a VM and ping on random existing provider network
- provider_net_nova_delete: Delete all VM's and provider network

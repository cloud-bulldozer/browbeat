#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import random

from rally.common import logging
from rally.common import sshutils

import dynamic_utils

LOG = logging.getLogger(__name__)

# This test simulates trunk subports using vlan interfaces inside the VM.
# It creates vlan interface for the subport and then adds it's MAC and ip.
# After packet reaching the vlan interface, reply packet has to be properly
# routed. This test adds this route like in this example,
# If vlan interface inside VM has to reply to jumphost, we add a route to jumphost
# via this vlan interface device
#
# sudo ip link add link eth0 name eth0.1 type vlan id 1
# sudo ip link set dev eth0.1 address {mac}
# sudo ip link set dev eth0.1 up
# sudo ip a a {address}/24 dev eth0.1
# sudo ip r a {vm2_address} via {gateway} dev eth0.1
#
# We can't use cirros image as it doesn't support vlans
# smallest flavor for centos is m1.tiny-centos (RAM 192, disk 8, vcpu 1)
#
# We have 3 other scenarios apart from the subport connection simulation mentioned
# above.
# 1. Add subports to random trunks
# 2. Delete subports from random trunks
# 3. Swap floating IPs between 2 random subports from 2 randomly chosen trunks

class TrunkDynamicScenario(
    dynamic_utils.NovaUtils,
    dynamic_utils.NeutronUtils,
    dynamic_utils.LockUtils
):
    def add_route_from_vm_to_jumphost(self, local_vm, dest_vm, local_vm_user,
                                      subport_number, gateway):
        """Add route from trunk vm to jumphost via trunk subport
        :param local_vm: floating ip of local VM
        :param dest_vm: floating ip of destination VM
        :param local_vm_user: str, ssh user for local VM
        :param subport_number: int, trunk subport on which route is created
        :param gateway: network gateway
        """
        script = f"sudo ip r a {dest_vm} via {gateway} dev eth0.{subport_number}"
        source_ssh = sshutils.SSH(
            local_vm_user, local_vm, pkey=self.keypair["private"]
        )
        self._wait_for_ssh(source_ssh)
        self._run_command_with_attempts(source_ssh, script)

    def delete_route_from_vm_to_jumphost(self, local_vm, dest_vm, local_vm_user,
                                         subport_number, gateway):
        """Delete route from trunk vm to jumphost via trunk subport
        :param local_vm: floating ip of local VM
        :param dest_vm: floating ip of destination VM
        :param local_vm_user: str, ssh user for local VM
        :param subport_number: int, trunk subport on which route is created
        :param gateway: network gateway
        """
        script = f"sudo ip r d {dest_vm} via {gateway} dev eth0.{subport_number}"
        source_ssh = sshutils.SSH(
            local_vm_user, local_vm, pkey=self.keypair["private"]
        )
        self._wait_for_ssh(source_ssh)
        self._run_command_with_attempts(source_ssh, script)

    def ping_subport_fip_from_jumphost(self, dest_vm, dest_vm_user,
                                       fip, port, success_on_ping_failure=False):
        """Ping subport floating ip from jumphost
        :param dest_vm: floating ip of destination VM
        :param dest_vm_user: str, ssh user for destination VM
        :param fip: floating ip of subport
        :param port: subport to ping from jumphost
        :param success_on_ping_failure: bool, flag to ping till failure/success
        """
        if not(success_on_ping_failure):
            fip_update_dict = {"port_id": port["id"]}
            self.clients("neutron").update_floatingip(
                fip["id"], {"floatingip": fip_update_dict}
            )

        address = fip["floating_ip_address"]
        dest_ssh = sshutils.SSH(dest_vm_user, dest_vm, pkey=self.keypair["private"])
        self._wait_for_ssh(dest_ssh)
        cmd = f"ping -c1 -w1 {address}"
        if success_on_ping_failure:
            self._run_command_until_failure(dest_ssh, cmd)
        else:
            self._run_command_with_attempts(dest_ssh, cmd)

    def simulate_subport_connection(self, trunk_id, vm_fip, jump_fip):
        """Simulate connection from jumphost to random subport of trunk VM
        :param trunk_id: id of trunk on which subport is present
        :param vm_fip: floating ip of trunk VM
        :param jump_fip: floating ip of jumphost
        """
        trunk = self.clients("neutron").show_trunk(trunk_id)
        subport_count = len(trunk["trunk"]["sub_ports"])
        subport_number_for_route = random.randint(1, subport_count)
        subport_for_route = self.clients("neutron").show_port(
            trunk["trunk"]["sub_ports"][subport_number_for_route-1]["port_id"])
        subnet_for_route = self.clients("neutron").show_subnet(
            subport_for_route["port"]["fixed_ips"][0]["subnet_id"])
        self.add_route_from_vm_to_jumphost(vm_fip, jump_fip, self.trunk_vm_user,
                                           subport_number_for_route,
                                           subnet_for_route["subnet"]["gateway_ip"])
        subport_fip = self._create_floatingip(self.ext_net_name)["floatingip"]
        self.ping_subport_fip_from_jumphost(jump_fip, self.jumphost_user, subport_fip,
                                            subport_for_route["port"])
        # We delete the route from vm to jumphost through the randomly
        # chosen subport after simulate subport connection is executed,
        # as additional subports can be tested for connection in the
        # add_subports_random_trunks function, and we would not want the
        # existing route created here to be used for those subports.
        self.delete_route_from_vm_to_jumphost(vm_fip, jump_fip, self.trunk_vm_user,
                                              subport_number_for_route,
                                              subnet_for_route["subnet"]["gateway_ip"])
        # Dissociate and delete floating IP as the same subport can be used
        # again later.
        self.dissociate_and_delete_floating_ip(subport_fip["id"])

    def get_server_by_trunk(self, trunk):
        """Get server details for a given trunk
        :param trunk: dict, trunk details
        :returns: floating ip of server
        """
        trunk_server = self._get_servers_by_tag("trunk:"+str(trunk["id"]))[0]
        trunk_server_fip = list(trunk_server.addresses.values())[0][1]["addr"]
        return trunk_server_fip

    def get_jumphost_by_trunk(self, trunk):
        """Get jumphost details for a given trunk
        :param trunk: dict, trunk details
        :returns: floating ip of jumphost
        """
        if trunk["description"].startswith("jumphost:"):
            jumphost_fip = trunk["description"][9:]
        return jumphost_fip

    def create_subnets_and_subports(self, subport_count):
        """Create <<subport_count>> subnets and subports
        :param subport_count: int, number of subports to create
        :returns: list of subnets, list of subports
        """
        subnets = []
        subports = []
        for _ in range(subport_count):
            net, subnet = self._create_network_and_subnets(network_create_args={})
            subnets.append(subnet[0])
            subports.append(
                self._create_port(
                    net,
                    {
                        "fixed_ips": [{"subnet_id": subnet[0]["subnet"]["id"]}],
                        "security_groups": [self.security_group["id"]],
                    },
                )
            )
            self._add_interface_router(subnet[0]["subnet"], self.router["router"])
        return subnets, subports

    def add_subports_to_trunk_and_vm(self, subports, trunk_id, vm_ssh, start_seg_id):
        """Add subports to trunk and create vlan interfaces for subports inside trunk VM
        :param subports: list, list of subports
        :param trunk_id: id of trunk to add subports
        :param vm_ssh: ssh connection to trunk VM
        :param start_seg_id: int, number of vlan interface to start subport addition
        """
        # Inside VM, subports are simulated (implemented) using vlan interfaces
        # Later we ping these vlan interfaces
        for seg_id, subport in enumerate(subports,
                                         start=start_seg_id):
            subport_payload = [
                {
                    "port_id": subport["port"]["id"],
                    "segmentation_type": "vlan",
                    "segmentation_id": seg_id,
                }
            ]
            self._add_subports_to_trunk(trunk_id, subport_payload)

            mac = subport["port"]["mac_address"]
            address = subport["port"]["fixed_ips"][0]["ip_address"]
            # Note: Manually assign ip as calling dnsmasq will also add
            # default route which will break floating ip for the VM
            cmd = f"sudo ip link add link eth0 name eth0.{seg_id} type vlan id {seg_id}"
            self._run_command_with_attempts(vm_ssh, cmd)
            cmd = f"sudo ip link set dev eth0.{seg_id} address {mac}"
            self._run_command_with_attempts(vm_ssh, cmd)
            cmd = f"sudo ip link set dev eth0.{seg_id} up"
            self._run_command_with_attempts(vm_ssh, cmd)
            cmd = f"sudo ip a a {address}/24 dev eth0.{seg_id}"
            self._run_command_with_attempts(vm_ssh, cmd)

    def pod_fip_simulation(self, ext_net_id, trunk_image, trunk_flavor,
                           jumphost_image, jumphost_flavor, subport_count, num_vms=1):
        """Simulate pods with floating ips using subports on trunks and VMs
        :param ext_net_id: external network ID for floating IP creation
        :param trunk_image: image ID or instance for trunk server creation
        :param trunk_flavor: int, flavor ID or instance for trunk server creation
        :param jumphost_image: image ID or instance for jumphost creation
        :param jumphost_flavor: int, flavor ID or instance for jumphost creation
        :param subport_count: int, number of subports to create per trunk
        :param num_vms: int, number of servers to create
        """
        self.ext_net_name = None
        if ext_net_id:
            self.ext_net_name = self.clients("neutron").show_network(ext_net_id)["network"][
                "name"
            ]

        self.trunk_vm_user = "centos"
        self.jumphost_user = "cirros"

        router_create_args = {}
        router_create_args["name"] = self.generate_random_name()
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault(
            "external_gateway_info", {"network_id": ext_net_id, "enable_snat": True}
        )
        self.router = self.admin_clients("neutron").create_router(
            {"router": router_create_args}
        )
        network = self._create_network({})
        subnet = self._create_subnet(network, {})
        self._add_interface_router(subnet["subnet"], self.router["router"])

        kwargs = {}
        kwargs["nics"] = [{"net-id": network["network"]["id"]}]
        self.keypair = self.context["user"]["keypair"]
        jump_host = self._boot_server_with_fip_and_tag(jumphost_image, jumphost_flavor,
                                                       "jumphost_trunk", True,
                                                       self.ext_net_name,
                                                       key_name=self.keypair["name"],
                                                       **kwargs)
        jump_fip = jump_host[1]["ip"]

        for _ in range(num_vms):
            kwargs = {}
            # create parent and trunk, boot the VM
            self.security_group = self.context["tenant"]["users"][0]["secgroup"]
            port_creates_args = {"security_groups": [self.security_group["id"]]}
            parent = self._create_port(network, port_creates_args)
            # Using tags for trunk returns an error,
            # so we instead use description.
            trunk_payload = {"port_id": parent["port"]["id"],
                             "description": "jumphost:"+str(jump_fip)}
            trunk = self._create_trunk(trunk_payload)
            kwargs["nics"] = [{"port-id": parent["port"]["id"]}]
            vm = self._boot_server_with_fip_and_tag(trunk_image, trunk_flavor,
                                                    "trunk:"+str(trunk["trunk"]["id"]), True,
                                                    self.ext_net_name,
                                                    key_name=self.keypair["name"],
                                                    **kwargs)
            vm_fip = vm[1]["ip"]

            subnets, subports = self.create_subnets_and_subports(subport_count)

            vm_ssh = sshutils.SSH(self.trunk_vm_user,
                                  vm_fip, pkey=self.keypair["private"])
            self._wait_for_ssh(vm_ssh)

            self.add_subports_to_trunk_and_vm(subports, trunk["trunk"]["id"], vm_ssh, 1)

            self.simulate_subport_connection(trunk["trunk"]["id"], vm_fip, jump_fip)

    def add_subports_to_random_trunks(self, num_trunks, subport_count):
        """Add <<subport_count>> subports to <<num_trunks>> randomly chosen trunks
        :param num_trunks: int, number of trunks to be randomly chosen
        :param subport_count: int, number of subports to add to each trunk
        """
        trunks = self._list_trunks()

        random.shuffle(trunks)
        initial_num_trunks = num_trunks
        num_trunks = min(2*num_trunks, len(trunks))
        trunks_to_add_subports = [trunks[i] for i in range(num_trunks)]

        loop_counter = 0
        num_operations_completed = 0

        while loop_counter < num_trunks and num_operations_completed < initial_num_trunks:
            trunk = trunks_to_add_subports[loop_counter]

            loop_counter += 1
            if not self.acquire_lock(trunk["id"]):
                continue

            subnets, subports = self.create_subnets_and_subports(subport_count)

            trunk_server_fip = self.get_server_by_trunk(trunk)
            jump_fip = self.get_jumphost_by_trunk(trunk)

            vm_ssh = sshutils.SSH(
                self.trunk_vm_user, trunk_server_fip, pkey=self.keypair["private"]
            )
            self._wait_for_ssh(vm_ssh)

            self.add_subports_to_trunk_and_vm(subports, trunk["id"],
                                              vm_ssh, len(trunk["sub_ports"])+1)

            self.simulate_subport_connection(trunk["id"], trunk_server_fip, jump_fip)
            self.release_lock(trunk["id"])
            num_operations_completed += 1

        if num_operations_completed == 0:
            LOG.info("""No trunks which are not under lock, so
                     cannot add subports to any trunks.""")

    def delete_subports_from_random_trunks(self, num_trunks, subport_count):
        """Delete <<subport_count>> subports from <<num_trunks>> randomly chosen trunks
        :param num_trunks: int, number of trunks to be randomly chosen
        :param subport_count: int, number of subports to add to each trunk
        """
        trunks = self._list_trunks()

        eligible_trunks = [trunk for trunk in trunks if len(trunk['sub_ports']) >= subport_count]
        initial_num_trunks = num_trunks
        num_trunks = min(2*num_trunks, len(trunks))
        random.shuffle(eligible_trunks)

        if len(eligible_trunks) >= num_trunks:
            trunks_to_delete_subports = [eligible_trunks[i] for i in range(num_trunks)]
        else:
            trunks_to_delete_subports = sorted(trunks,
                                               key=lambda k:-len(k['sub_ports']))[:num_trunks]
            subport_count = len(trunks_to_delete_subports[-1]['sub_ports'])

        loop_counter = 0
        num_operations_completed = 0

        while loop_counter < num_trunks and num_operations_completed < initial_num_trunks:
            trunk = trunks_to_delete_subports[loop_counter]

            loop_counter += 1
            if not self.acquire_lock(trunk["id"]):
                continue

            trunk_server_fip = self.get_server_by_trunk(trunk)
            jump_fip = self.get_jumphost_by_trunk(trunk)

            vm_ssh = sshutils.SSH(self.trunk_vm_user,
                                  trunk_server_fip, pkey=self.keypair["private"])
            self._wait_for_ssh(vm_ssh)

            trunk_subports = trunk['sub_ports']
            num_trunk_subports = len(trunk_subports)

            # We delete subports from trunks starting from the last subport,
            # instead of randomly. This is because deleting random subports
            # might cause a lot of conflict with the add_subports_to_random_
            # trunks function.
            for subport_number in range(num_trunk_subports-1,
                                        num_trunk_subports-1-subport_count, -1):
                subport_details = trunk_subports[subport_number]
                subport_to_delete = self.clients("neutron").show_port(subport_details["port_id"])
                subport_payload = [
                    {
                        "port_id": subport_to_delete["port"]["id"],
                        "segmentation_type": "vlan",
                        "segmentation_id": subport_number+1,
                    }
                ]

                cmd = f"sudo ip link delete eth0.{subport_number+1}"
                self._run_command_with_attempts(vm_ssh,cmd)
                self.clients("neutron").trunk_remove_subports(trunk["id"],
                                                              {"sub_ports": subport_payload})
                self.clients("neutron").delete_port(subport_to_delete["port"]["id"])

            # Check the number of subports present in trunk after deletion,
            # and simulate subport connection if it is > 0. We use the
            # show_trunk function here to get updated information about the
            # trunk, as the trunk loop variable will have whatever information
            # was valid at the beginning of the loop.
            if len(self.clients("neutron").show_trunk(trunk["id"])["trunk"]["sub_ports"]) > 0:
                self.simulate_subport_connection(trunk["id"], trunk_server_fip, jump_fip)

            self.release_lock(trunk["id"])
            num_operations_completed += 1

        if num_operations_completed == 0:
            LOG.info("""No trunks which are not under lock, so
                     cannot delete subports from any trunks.""")

    def swap_floating_ips_between_random_subports(self):
        """Swap floating IPs between 2 randomly chosen subports from 2 trunks
        """
        trunks = [trunk for trunk in self._list_trunks() if len(trunk["sub_ports"]) > 0]

        if len(trunks) < 2:
            LOG.info("""Number of eligible trunks not sufficient
                     for swapping floating IPs between trunk subports""")
            return

        trunks_for_swapping = []
        for trunk in trunks:
            if not self.acquire_lock(trunk["id"]):
                continue
            trunks_for_swapping.append(trunk)
            if len(trunks_for_swapping) == 2:
                break

        if len(trunks_for_swapping) < 2:
            LOG.info("""Number of unlocked trunks not sufficient
                     for swapping floating IPs between trunk subports""")
            return

        jumphost1_fip = self.get_jumphost_by_trunk(trunks_for_swapping[0])
        jumphost2_fip = self.get_jumphost_by_trunk(trunks_for_swapping[1])

        trunk_vm1_fip = self.get_server_by_trunk(trunks_for_swapping[0])
        trunk_vm2_fip = self.get_server_by_trunk(trunks_for_swapping[1])

        subport1_count = len(trunks_for_swapping[0]["sub_ports"])
        subport1_number_for_route = random.randint(1, subport1_count)
        subport1 = self.clients("neutron").show_port(
            trunks_for_swapping[0]["sub_ports"][subport1_number_for_route-1]["port_id"])
        subnet1 = self.clients("neutron").show_subnet(
            subport1["port"]["fixed_ips"][0]["subnet_id"])
        self.add_route_from_vm_to_jumphost(trunk_vm1_fip, jumphost1_fip, self.trunk_vm_user,
                                           subport1_number_for_route,
                                           subnet1["subnet"]["gateway_ip"])

        subport2_count = len(trunks_for_swapping[1]["sub_ports"])
        subport2_number_for_route = random.randint(1, subport2_count)
        subport2 = self.clients("neutron").show_port(
            trunks_for_swapping[1]["sub_ports"][subport2_number_for_route-1]["port_id"])
        subnet2 = self.clients("neutron").show_subnet(
            subport2["port"]["fixed_ips"][0]["subnet_id"])
        self.add_route_from_vm_to_jumphost(trunk_vm2_fip, jumphost2_fip, self.trunk_vm_user,
                                           subport2_number_for_route,
                                           subnet2["subnet"]["gateway_ip"])

        subport1_fip = self.create_floating_ip_and_associate_to_port(subport1, self.ext_net_name)
        subport2_fip = self.create_floating_ip_and_associate_to_port(subport2, self.ext_net_name)

        fip_update_dict = {"port_id": None}
        self.clients("neutron").update_floatingip(
            subport1_fip["id"], {"floatingip": fip_update_dict})
        self.clients("neutron").update_floatingip(
            subport2_fip["id"], {"floatingip": fip_update_dict})

        LOG.info("Ping until failure after dissociating subports' floating IPs, before swapping")
        self.ping_subport_fip_from_jumphost(jumphost1_fip, self.jumphost_user, subport1_fip,
                                            subport1["port"], True)
        self.ping_subport_fip_from_jumphost(jumphost2_fip, self.jumphost_user, subport2_fip,
                                            subport2["port"], True)

        LOG.info("Ping until success by swapping subports' floating IPs")
        self.ping_subport_fip_from_jumphost(jumphost1_fip, self.jumphost_user, subport2_fip,
                                            subport1["port"])
        self.ping_subport_fip_from_jumphost(jumphost2_fip, self.jumphost_user, subport1_fip,
                                            subport2["port"])

        self.delete_route_from_vm_to_jumphost(trunk_vm1_fip, jumphost1_fip, self.trunk_vm_user,
                                              subport1_number_for_route,
                                              subnet1["subnet"]["gateway_ip"])

        self.delete_route_from_vm_to_jumphost(trunk_vm2_fip, jumphost2_fip, self.trunk_vm_user,
                                              subport2_number_for_route,
                                              subnet2["subnet"]["gateway_ip"])

        # Dissociate and delete floating IPs as the same subports can be used
        # again later.
        self.dissociate_and_delete_floating_ip(subport1_fip["id"])
        self.dissociate_and_delete_floating_ip(subport2_fip["id"])

        # Release lock from trunks
        self.release_lock(trunks_for_swapping[0]["id"])
        self.release_lock(trunks_for_swapping[1]["id"])

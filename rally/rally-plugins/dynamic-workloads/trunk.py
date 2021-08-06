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

from rally_openstack.scenarios.neutron import utils as neutron_utils
import nova_custom

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
# Note: Though we are creating vlan interface for each subport, ping test
# will test only first vlan interface (i.e first subport)
#
# We can't use cirros image as it doesn't support vlans
# smallest flavor for centos is m1.tiny-centos (RAM 192, disk 8, vcpu 1)
#
# We also have a scenario to add subports to random trunks in this test.


class TrunkDynamicScenario(
    nova_custom.NovaDynamicScenario, neutron_utils.NeutronScenario
):
    def simulate_subport_connection(self, local_vm, dest_vm, local_vm_user,
                                    dest_vm_user, fip, port, gateway, add_route=False):
        """Simulate subport connection from jumphost to VM.
        :param local_vm: floating ip of local VM
        :param dest_vm: floating ip of destination VM
        :param local_vm_user: str, ssh user for local VM
        :param dest_vm_user: str, ssh user for destination VM
        :param fip: floating ip of subport
        :param port: subport to ping from jumphost
        :param gateway: network gateway
        """
        fip_update_dict = {"port_id": port["id"]}
        self.clients("neutron").update_floatingip(
            fip["id"], {"floatingip": fip_update_dict}
        )
        if add_route:
            script = f"sudo ip r a {dest_vm} via {gateway} dev eth0.1"
            source_ssh = sshutils.SSH(
                local_vm_user, local_vm, pkey=self.keypair["private"]
            )
            self._wait_for_ssh(source_ssh)
            self._run_command_with_attempts(source_ssh, script)

        address = fip["floating_ip_address"]
        dest_ssh = sshutils.SSH(dest_vm_user, dest_vm, pkey=self.keypair["private"])
        self._wait_for_ssh(dest_ssh)
        cmd = f"ping -c1 -w1 {address}"
        self._run_command_with_attempts(dest_ssh, cmd)

    def get_server_by_trunk(self, trunk, servers):
        """Get server details for a given trunk
        :param trunk: dict, trunk details
        :param servers: list, list of server objects to search
        :returns: floating ip of server, server object
        """
        for server in servers:
            for interface in self._list_interfaces(server):
                if interface._info["port_id"] == trunk["port_id"]:
                    trunk_server_fip = list(server.addresses.values())[0][1]["addr"]
                    trunk_server = server
                    break
        return trunk_server_fip, trunk_server

    def pod_fip_simulation(self, ext_net_id, image, flavor, subport_count, num_vms=1):
        """Simulate pods with floating ips using subports on trunks and VMs
        :param ext_net_id: external network ID for floating IP creation
        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param subport_count: int, number of subports to create per trunk
        :param num_vms: int, number of servers to create
        """
        ext_net_name = None
        if ext_net_id:
            ext_net_name = self.clients("neutron").show_network(ext_net_id)["network"][
                "name"
            ]

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
        images = self.clients("glance").images.list()
        jump_host_image = [i.id for i in images if i.name == "cirros"][0]
        flavors = self._list_flavors()
        jump_host_flavor = [f.id for f in flavors if f.name == "m1.xtiny"][0]
        jump_host = self._boot_server_with_fip(
            jump_host_image,
            jump_host_flavor,
            True,
            ext_net_name,
            key_name=self.keypair["name"],
            **kwargs,
        )
        jump_fip = jump_host[1]["ip"]

        images = self.clients("glance").images.list()
        image_name = [i.name for i in images if str(i.id) == image][0]
        if image_name == "centos7":
            vm_user = "centos"
        elif image_name == "cirros":
            vm_user = "cirros"

        for _ in range(num_vms):
            kwargs = {}
            # create parent and trunk, boot the VM
            self.security_group = self.context["tenant"]["users"][0]["secgroup"]
            port_creates_args = {"security_groups": [self.security_group["id"]]}
            parent = self._create_port(network, port_creates_args)
            trunk_payload = {"port_id": parent["port"]["id"]}
            trunk = self._create_trunk(trunk_payload)
            kwargs["nics"] = [{"port-id": parent["port"]["id"]}]
            vm = self._boot_server_with_fip(
                image,
                flavor,
                True,
                ext_net_name,
                key_name=self.keypair["name"],
                **kwargs,
            )
            vm_fip = vm[1]["ip"]

            subnets = []
            subports = []
            for _ in range(subport_count + 1):
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

            vm_ssh = sshutils.SSH(vm_user, vm_fip, pkey=self.keypair["private"])
            self._wait_for_ssh(vm_ssh)

            # Inside VM, subports are simulated (implemented) using vlan interfaces
            # Later we ping these vlan interfaces
            for seg_id, p in enumerate(subports, start=1):
                subport_payload = [
                    {
                        "port_id": p["port"]["id"],
                        "segmentation_type": "vlan",
                        "segmentation_id": seg_id,
                    }
                ]
                self._add_subports_to_trunk(trunk["trunk"]["id"], subport_payload)

                mac = p["port"]["mac_address"]
                address = p["port"]["fixed_ips"][0]["ip_address"]
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

            subport_fip = self._create_floatingip(ext_net_name)["floatingip"]
            self.simulate_subport_connection(
                vm_fip,
                jump_fip,
                vm_user,
                "cirros",
                subport_fip,
                subports[0]["port"],
                subnets[0]["subnet"]["gateway_ip"],
                True,
            )

    def add_subports_to_random_trunks(self, num_trunks, subport_count):
        """Add <<subport_count>> subports to <<num_trunks>> randomly chosen trunks
        :param num_trunks: int, number of trunks to be randomly chosen
        :param subport_count: int, number of subports to add to each trunk
        """
        trunks = self._list_trunks()
        servers = self._list_servers(True)

        random.shuffle(trunks)
        num_trunks = min(num_trunks, len(trunks))
        trunks_to_add_subports = [trunks[i] for i in range(num_trunks)]

        for trunk in trunks_to_add_subports:
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

            trunk_server_fip, trunk_server = self.get_server_by_trunk(trunk, servers)

            images = self.clients("glance").images.list()
            image_name = [
                i.name for i in images if str(i.id) == trunk_server._info["image"]["id"]
            ][0]
            if image_name == "centos7":
                vm_user = "centos"
            elif image_name == "cirros":
                vm_user = "cirros"

            vm_ssh = sshutils.SSH(
                vm_user, trunk_server_fip, pkey=self.keypair["private"]
            )
            self._wait_for_ssh(vm_ssh)

            for seg_id, p in enumerate(subports, start=len(trunk["sub_ports"]) + 1):
                subport_payload = [
                    {
                        "port_id": p["port"]["id"],
                        "segmentation_type": "vlan",
                        "segmentation_id": seg_id,
                    }
                ]
                self._add_subports_to_trunk(trunk["id"], subport_payload)

                mac = p["port"]["mac_address"]
                address = p["port"]["fixed_ips"][0]["ip_address"]
                cmd = f"sudo ip link add link eth0 name eth0.{seg_id} type vlan id {seg_id}"
                self._run_command_with_attempts(vm_ssh, cmd)
                cmd = f"sudo ip link set dev eth0.{seg_id} address {mac}"
                self._run_command_with_attempts(vm_ssh, cmd)
                cmd = f"sudo ip link set dev eth0.{seg_id} up"
                self._run_command_with_attempts(vm_ssh, cmd)
                cmd = f"sudo ip a a {address}/24 dev eth0.{seg_id}"
                self._run_command_with_attempts(vm_ssh, cmd)

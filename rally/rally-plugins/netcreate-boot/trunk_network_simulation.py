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

import time

from rally.common import logging
from rally.common import sshutils

from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally_openstack.scenarios.vm import utils as vm_utils
from rally_openstack import consts
from rally.task import scenario
from rally.task import validation


LOG = logging.getLogger(__name__)

# This test simulates trunk subports using vlan interfaces inside the VM.
# It creates vlan interface for the subport and then adds it's MAC and ip.
# After packet reaching the vlan interface, reply packet has to be properly
# routed. This test adds this route like in this example,
# If vlan interface inside VM1 has to reply to VM2, we add a route to VM2
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

@validation.add("required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"], "keypair@openstack": {},
                             "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.trunk_subport_connection", platform="openstack")
class TrunkSubportConnection(vm_utils.VMScenario,
                             neutron_utils.NeutronScenario):

    def _run_command(self, ssh_connection, cmd, max_attempts=120):
        attempts = 0
        while attempts < max_attempts:
            status, out, err = ssh_connection.execute(cmd)
            LOG.info("attempt: {} cmd: {}, status:{}".format(
                attempts, cmd, status))
            if status != 0:
                attempts += 1
                time.sleep(2)
            else:
                break
        if (attempts == max_attempts) and (status != 0):
            LOG.info(
                "Error running command %(command)s. "
                "Error %(code)s: %(error)s" %
                {"command": cmd, "code": status, "error": err})
        else:
            LOG.info("Command executed successfully: %(command)s" % {"command": cmd})

    def create_trunk_with_subports(self, ext_net_id, ext_net_name, image, flavor, subport_count):
        router_create_args = {}
        router_create_args["name"] = self.generate_random_name()
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault("external_gateway_info",
                                      {"network_id": ext_net_id, "enable_snat": True})
        router = self.admin_clients("neutron").create_router(
            {"router": router_create_args})

        network = self._create_network({})
        subnet = self._create_subnet(network, {})
        self._add_interface_router(subnet['subnet'], router['router'])

        kwargs = {}
        # create parent and trunk, boot the VM
        security_group = self.context["tenant"]["users"][0]["secgroup"]
        port_creates_args = {"security_groups": [security_group["id"]]}
        parent = self._create_port(network, port_creates_args)
        trunk_payload = {"port_id": parent["port"]["id"]}
        trunk = self._create_trunk(trunk_payload)
        kwargs["nics"] = [{"port-id": parent["port"]["id"]}]
        self.keypair = self.context["user"]["keypair"]
        guest = self._boot_server_with_fip(
            image, flavor, True, ext_net_name,
            key_name=self.keypair["name"], **kwargs)
        fip = guest[1]['ip']

        subnets = []
        subports = []
        for i in range(subport_count + 1):
            net, subnet = self._create_network_and_subnets(
                network_create_args={})
            subnets.append(subnet[0])
            subports.append(self._create_port(
                net, {"fixed_ips": [{
                      "subnet_id": subnet[0]["subnet"]["id"]}],
                      "security_groups": [security_group["id"]]}))
            self._add_interface_router(subnet[0]['subnet'], router['router'])

        jump_ssh = sshutils.SSH("centos", fip, pkey=self.keypair["private"])
        self._wait_for_ssh(jump_ssh)

        # Inside VM, subports are simulated (implemented) using vlan interfaces
        # Latest we ping these vlan interfaces
        for seg_id, p in enumerate(subports, start=1):
            subport_payload = [{"port_id": p["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": seg_id}]
            self._add_subports_to_trunk(trunk["trunk"]["id"], subport_payload)

            mac = p["port"]["mac_address"]
            address = p["port"]["fixed_ips"][0]["ip_address"]
            # Note: Manually assign ip as calling dnsmasq will also add
            # default route which will break floating ip for the VM
            cmd = f"sudo ip link add link eth0 name eth0.{seg_id} type vlan id {seg_id}"
            self._run_command(jump_ssh,cmd)
            cmd = f"sudo ip link set dev eth0.{seg_id} address {mac}"
            self._run_command(jump_ssh,cmd)
            cmd = f"sudo ip link set dev eth0.{seg_id} up"
            self._run_command(jump_ssh,cmd)
            cmd = f"sudo ip a a {address}/24 dev eth0.{seg_id}"
            self._run_command(jump_ssh,cmd)

        # We test connection to first subport
        return fip, subnets[0]["subnet"]["gateway_ip"], subports[0]["port"]

    def simulate_subport_connection(self, local_vm, dest_vm, fip,
                                    port, gateway, add_route=False):
        fip_update_dict = {"port_id": port["id"]}
        self.clients("neutron").update_floatingip(
            fip["id"], {"floatingip": fip_update_dict}
        )
        if add_route:
            script = f"sudo ip r a {dest_vm} via {gateway} dev eth0.1"
            local_ssh = sshutils.SSH("centos", local_vm, pkey=self.keypair["private"])
            self._wait_for_ssh(local_ssh)
            self._run_command(local_ssh,script)

        address = fip["floating_ip_address"]
        dest_ssh = sshutils.SSH("centos", dest_vm, pkey=self.keypair["private"])
        self._wait_for_ssh(dest_ssh)
        cmd = f"ping -c1 -w1 {address}"
        self._run_command(dest_ssh,cmd)

    def test_trunk_subport_connection(self, ext_net_id, image_name='centos7',
                                      flavor_name='m1.tiny-centos', subport_count=1):
        images = self.clients("glance").images.list()
        image = [i.id for i in images if i.name == image_name][0]
        flavors = self._list_flavors()
        flavor = [i.id for i in flavors if i.name == flavor_name][0]

        ext_net_name = None
        if ext_net_id:
            ext_net_name = self.clients("neutron").show_network(
                ext_net_id)["network"]["name"]
        fip1 = self._create_floatingip(ext_net_name)["floatingip"]
        fip2 = self._create_floatingip(ext_net_name)["floatingip"]

        vm1, gateway1, subport1 = self.create_trunk_with_subports(
            ext_net_id, ext_net_name, image, flavor, subport_count)
        vm2, gateway2, subport2 = self.create_trunk_with_subports(
            ext_net_id, ext_net_name, image, flavor, subport_count)

        self.simulate_subport_connection(
            vm1, vm2, fip1, subport1, gateway1, True)
        self.simulate_subport_connection(
            vm2, vm1, fip2, subport2, gateway2, True)

        # swap floating ip across subports i.e vm1's subport fip assigned to
        # vm2's subport and vice versa
        fip_update_dict = {"port_id": None}
        self.clients("neutron").update_floatingip(
            fip1["id"], {"floatingip": fip_update_dict})
        self.clients("neutron").update_floatingip(
            fip2["id"], {"floatingip": fip_update_dict})

        self.simulate_subport_connection(vm1, vm2, fip2, subport1, gateway1)
        self.simulate_subport_connection(vm2, vm1, fip1, subport2, gateway2)

    def run(self, ext_net_id, num_subports=1, **kwargs):
        self.test_trunk_subport_connection(
            ext_net_id, subport_count=num_subports)

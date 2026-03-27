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

import logging
import subprocess
from ipaddress import ip_network
from rally.task import atomic
from rally.task import scenario
from rally.task import types
from rally.task import validation
from rally_openstack.common import consts
from rally_openstack.task.scenarios.neutron import utils as neutron_utils
from rally_openstack.task.scenarios.vm import utils as vm_utils
from rally.utils import sshutils

LOG = logging.getLogger(__name__)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(
    context={
        "cleanup@openstack": ["neutron", "nova"],
        "keypair@openstack": {},
        "allow_ssh@openstack": None
    },
    name="BrowbeatPlugin.create_provider_net_nova_boot_ping_ssh",
    platform="openstack"
)
class CreateProviderNetNovaBootPingSSH(vm_utils.VMScenario, neutron_utils.NeutronScenario):

    def run(self, image, flavor, provider_phys_net, iface_name, base_vlan,
            username, ssh_timeout=120, subnet_create_args=None, **kwargs):

        self.keypair = self.context["user"]["keypair"]
        vlan_id = base_vlan + self.context.get("iteration")

        network = self._create_network(provider_phys_net, vlan_id)
        subnet = self._create_subnet(network, subnet_create_args or {})
        kwargs["nics"] = [{"net-id": network["network"]["id"]}]
        kwargs["key_name"] = self.keypair["name"]

        gateway = subnet["subnet"]["gateway_ip"]
        cidr = subnet["subnet"]["cidr"]
        prefix = ip_network(cidr).prefixlen

        vlan_iface = f"{iface_name}.{vlan_id}"
        vlan_setup_done = False
        try:
            LOG.info(
                "Setting up bastion VLAN interface %s",
                vlan_iface
            )
            vlan_setup_cmds = [
                ["sudo", "ip", "link", "add", "link", iface_name,
                 "name", vlan_iface, "type", "vlan", "id", str(vlan_id)],
                ["sudo", "ip", "addr", "add", f"{gateway}/{prefix}",
                 "dev", vlan_iface],
                ["sudo", "ip", "link", "set", vlan_iface, "up"],
            ]
            for cmd in vlan_setup_cmds:
                result = subprocess.run(
                    cmd, capture_output=True, text=True
                )
                if result.returncode != 0:
                    LOG.error(
                        "Command %s failed with stderr: %s",
                        " ".join(cmd), result.stderr
                    )
                    raise Exception(
                        f"Failed to setup VLAN interface {vlan_iface}"
                    )
            vlan_setup_done = True
            server = self._boot_server(image, flavor, **kwargs)

            internal_network = list(server.networks)[0]
            server_ip = server.addresses[internal_network][0]["addr"]
            LOG.info("Waiting for ping response from %s", server_ip)
            self._wait_for_ping(server_ip)
            LOG.info("Ping to %s is successful", server_ip)
            pkey = self.keypair["private"]
            ssh = sshutils.SSH(
                username, server_ip, port=22, pkey=pkey
            )
            LOG.info("Waiting for SSH on %s", server_ip)
            self._wait_for_ssh(ssh, timeout=ssh_timeout)
            LOG.info("SSH to %s is successful", server_ip)
        finally:
            if vlan_setup_done:
                LOG.info(
                    "Cleaning up bastion VLAN interface %s",
                    vlan_iface
                )
                result = subprocess.run(
                    ["sudo", "ip", "link", "delete", vlan_iface],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    LOG.error(
                        "Failed to delete VLAN interface %s: %s",
                        vlan_iface, result.stderr
                    )

    @atomic.action_timer("neutron.create_network")
    def _create_network(self, provider_phys_net, vlan_id):
        """Create provider network with explicit VLAN ID."""
        project_id = self.context["tenant"]["id"]
        body = {
            "name": self.generate_random_name(),
            "tenant_id": project_id,
            "provider:network_type": "vlan",
            "provider:physical_network": provider_phys_net,
            "provider:segmentation_id": vlan_id
        }
        return self.admin_clients("neutron").create_network(
            {"network": body}
        )

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
import os
import subprocess

from rally_openstack.common import consts
from rally_openstack.task.scenarios.neutron import utils as neutron_utils
from rally_openstack.task.scenarios.vm import utils as vm_utils
from rally.task import atomic
from rally.task import scenario
from rally.task import types
from rally.task import validation


LOG = logging.getLogger(__name__)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"], "keypair@openstack": {},
                             "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.create_provider_net_nova_boot_ping", platform="openstack")
class CreateProviderNetNovaBootPing(vm_utils.VMScenario,
                                    neutron_utils.NeutronScenario):

    def run(self, image, flavor, provider_phys_net, iface_name, iface_mac,
            num_vms=1, router_create_args=None,
            network_create_args=None, subnet_create_args=None, **kwargs):
        network = self._create_network(provider_phys_net)
        subnet = self._create_subnet(network, subnet_create_args or {})
        kwargs["nics"] = [{'net-id': network['network']['id']}]
        server = self._boot_server(image, flavor, **kwargs)

        # ping server
        internal_network = list(server.networks)[0]
        server_ip = server.addresses[internal_network][0]["addr"]
        server_mac = server.addresses[internal_network][0]["OS-EXT-IPS-MAC:mac_addr"]
        gateway = subnet['subnet']['gateway_ip']
        vlan = network['network']['provider:segmentation_id']

        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "scapy_icmp.py")
        cmd = ["sudo", file_path, server_ip, server_mac, gateway, iface_mac, iface_name, str(vlan)]
        proc = subprocess.Popen(cmd)
        proc.wait()
        if proc.returncode == 0:
            LOG.info("Ping to {} is succesful".format(server_ip))
        else:
            LOG.info("Ping to {} is failed".format(server_ip))

    @atomic.action_timer("neutron.create_network")
    def _create_network(self, provider_phys_net):
        """Create neutron provider network.

        :param provider_phys_net: provider physical network
        :returns: neutron network dict
        """
        project_id = self.context["tenant"]["id"]
        body = {
            "name": self.generate_random_name(),
            "tenant_id": project_id,
            "provider:network_type": "vlan",
            "provider:physical_network": provider_phys_net
        }
        # provider network can be created by admin client only
        return self.admin_clients("neutron").create_network({"network": body})

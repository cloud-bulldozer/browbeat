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
from rally_openstack.task.scenarios.vm import utils as vm_utils
from rally_openstack.task.scenarios.neutron import utils as neutron_utils
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
                    name="BrowbeatPlugin.nova_boot_from_context_provider_networks_ping",
                    platform="openstack")
class NovaBootFromContextProviderNetworksPing(vm_utils.VMScenario,
                                              neutron_utils.NeutronScenario):

    def run(self, image, flavor, num_provider_networks, ping_timeout, **kwargs):
        network_id = self.context["provider_networks"][((self.context["iteration"]-1)
                                                       % num_provider_networks)]["id"]
        network = self._show_provider_network(network_id)
        subnet = self.context["provider_subnets"][network_id]
        kwargs["nics"] = [{'net-id': network_id}]
        server = self._boot_server(image, flavor, **kwargs)

        # ping server
        internal_network = list(server.networks)[0]
        server_ip = server.addresses[internal_network][0]["addr"]
        server_mac = server.addresses[internal_network][0]["OS-EXT-IPS-MAC:mac_addr"]
        gateway = subnet['gateway_ip']
        vlan = network['network']['provider:segmentation_id']

        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "scapy_icmp.py")

        with atomic.ActionTimer(self, "nova.wait_for_custom_ping"):
            cmd = ["sudo", file_path, server_ip, server_mac, gateway, self.context["iface_mac"],
                   self.context["iface_name"], str(vlan)]
            proc = subprocess.Popen(cmd, start_new_session=True)
            try:
                proc.wait(timeout=ping_timeout)
            except subprocess.TimeoutExpired:
                pgid = os.getpgid(proc.pid)
                procout = subprocess.check_output(['sudo', 'kill', str(pgid)]).decode("utf-8")
                if not procout:
                    LOG.info("{} process group terminated successfully".format(pgid))
                else:
                    LOG.info("{} process group did not terminate successfully. Stdout : {}".format(
                             pgid, procout))
                raise Exception("Rally tired waiting {} seconds for ping to {}".format(
                                ping_timeout, server_ip))

        if proc.returncode == 0:
            LOG.info("Ping to {} is successful".format(server_ip))
        else:
            raise Exception("Ping to {} has failed".format(server_ip))

    @atomic.action_timer("neutron.show_network")
    def _show_provider_network(self, provider_network_id):
        """Fetches information of a certain provider network.
        :param provider_network: provider network object
        """

        return self.admin_clients("neutron").show_network(provider_network_id)

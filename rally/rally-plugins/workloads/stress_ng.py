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

from rally_openstack.common import consts
from rally.task import scenario
from rally.task import types
from rally.task import validation
import stress_ng_utils

@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("number", param_name="port", minval=1, maxval=65535,
                nullable=True, integer_only=True)
@validation.add("external_network_exists", param_name="floating_network")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_param_or_context",
                param_name="image", ctx_name="image_command_customizer")
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.stress_ng",
                    platform="openstack")
class BrowbeatStressNg(stress_ng_utils.BrowbeatStressNgUtils):

    def run(self, flavor, username, ssh_timeout, num_clients,
            command, image=None, floating_network=None, port=22,
            use_floating_ip=True, nova_api_version=2.52, **kwargs):
        """Create a jumphost on network with fip and all
           other vm's on the same neutron network so that jumphost
           can access the other vm's and run the stress tests

        :param flavor: VM flavor name
        :param username: ssh username on server
        :param ssh_timeout: ssh timeout in seconds
        :param num_clients: no.of clients
        :param command: command that runs inside the client vm's
        :param image: VM image name
        :param floating_network: external network name, for floating ip
        :param port: ssh port for SSH connection
        :param use_floating_ip: bool, floating or fixed IP for SSH connection
        :param nova_api_version: api microversion of nova
        :param kwargs: optional args to create a VM
        """
        self.run_stress_ng_on_clients(flavor, username, ssh_timeout, num_clients,
                                      command, image, floating_network, port,
                                      use_floating_ip, "stressng",
                                      nova_api_version, **kwargs)

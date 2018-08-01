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

from rally_openstack import consts
from rally_openstack.scenarios.nova import utils as nova_utils
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally.task import scenario
from rally.task import types
from rally.task import validation


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services",services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"]},
                    name="BrowbeatPlugin.create_network_nova_boot", platform="openstack")
class CreateNetworkNovaBoot(neutron_utils.NeutronScenario,
                            nova_utils.NovaScenario):

    def run(self, image, flavor, num_networks=1, network_create_args=None,
            subnet_create_args=None, **kwargs):
        nets = []
        for net in range(0, num_networks):
            network = self._create_network(network_create_args or {})
            self._create_subnet(network, subnet_create_args or {})
            nets.append(network)

        kwargs["nics"] = []
        for net in nets:
            kwargs["nics"].append({'net-id': net['network']['id']})

        self._boot_server(image, flavor, **kwargs)

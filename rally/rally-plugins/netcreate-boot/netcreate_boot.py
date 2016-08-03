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

from rally.task import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.task import types
from rally.task import validation


class BrowbeatPlugin(neutron_utils.NeutronScenario,
                     nova_utils.NovaScenario,
                     scenario.Scenario):

    @types.convert(image={"type": "glance_image"},
                   flavor={"type": "nova_flavor"})
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova", "neutron"]})
    def create_network_nova_boot(self, image, flavor, num_networks=1, network_create_args=None,
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

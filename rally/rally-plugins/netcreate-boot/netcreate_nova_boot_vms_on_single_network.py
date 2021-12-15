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

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../reports')))
from generate_scenario_duration_charts import ScenarioDurationChartsGenerator  # noqa: E402

@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services",services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"]},
                    name="BrowbeatPlugin.create_vms_on_network", platform="openstack")
class CreateVMsOnSingleNetwork(neutron_utils.NeutronScenario,
                               nova_utils.NovaScenario):

    def run(self, image, flavor, num_vms=1, network_create_args=None,
            subnet_create_args=None, port_create_args=None, **kwargs):

        network = self._create_network(network_create_args or {})
        self._create_subnet(network, subnet_create_args or {})

        for i in range(num_vms):
            kwargs["nics"] = []
            port = self._create_port(network, port_create_args or {})
            kwargs["nics"].append({'port-id': port['port']['id']})
            self._boot_server(image, flavor, **kwargs)

        self.duration_charts_generator = ScenarioDurationChartsGenerator()
        self.duration_charts_generator.add_per_iteration_complete_data(self)
        self.duration_charts_generator.add_duplicate_atomic_actions_iteration_additive_data(self)
        self.duration_charts_generator.add_all_resources_additive_data(self)

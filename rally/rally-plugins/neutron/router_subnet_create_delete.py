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
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally.task import scenario
from rally.task import validation


@validation.add("required_services",services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="BrowbeatPlugin.router_subnet_create_delete", platform="openstack")
class RouterSubnetCreateDelete(neutron_utils.NeutronScenario):

    def run(self, num_networks=1, network_create_args=None, subnet_create_args=None, **kwargs):
        router = self._create_router({})
        subnets = []
        for net in range(num_networks):
            network = self._create_network(network_create_args or {})
            subnet = self._create_subnet(network, subnet_create_args or {})
            subnets.append(subnet)
            self._add_interface_router(subnet['subnet'],router['router'])
        for subnet in subnets :
            self._remove_interface_router(subnet['subnet'],router['router'])

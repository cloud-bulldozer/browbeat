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
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.task import types
from rally.task import validation

class NeutronPlugin(neutron_utils.NeutronScenario,
                    scenario.Scenario):
    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_router_and_net(self,num_networks=1,network_create_args=None,
                              subnet_create_args=None,**kwargs):
        router = self._create_router({})
        subnets = []
        if num_networks == 1 :
            network = self._create_network(network_create_args or {})
            subnet = self._create_subnet(network, subnet_create_args or {})
            subnets.append(subnet)
            self._add_interface_router(subnet['subnet'],router['router'])
        else :
            for net in range(1,num_networks):
                network = self._create_network(network_create_args or {})
                subnet = self._create_subnet(network, subnet_create_args or {})
                subnets.append(subnet)
                self._add_interface_router(subnet['subnet'],router['router'])
        for subnet in subnets :
            self._remove_interface_router(subnet['subnet'],router['router'])

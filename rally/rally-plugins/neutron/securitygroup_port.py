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
                    name="BrowbeatPlugin.securitygroup_port", platform="openstack")
class BrowbeatPlugin(neutron_utils.NeutronScenario):

    def run(self, network_create_args=None, security_group_create_args={}, port_create_args={},
            **kwargs):
        net = self._create_network(network_create_args or {})
        sec_grp = self._create_security_group(**security_group_create_args)
        sec_grp_list = []
        sec_grp_list.append(sec_grp['security_group']['id'])
        port_create_args['security_groups'] = sec_grp_list
        port = self._create_port(net, port_create_args)
        self._delete_port(port)
        self._delete_security_group(sec_grp)

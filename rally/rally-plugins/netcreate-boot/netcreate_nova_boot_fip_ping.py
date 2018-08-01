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
from rally_openstack.scenarios.vm import utils as vm_utils
from rally.task import atomic
from rally.task import scenario
from rally.task import types
from rally.task import validation


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"], "keypair@openstack": {},
                             "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.create_network_nova_boot_ping", platform="openstack")
class CreateNetworkNovaBootPing(neutron_utils.NeutronScenario,
                                vm_utils.VMScenario):

    def run(self, image, flavor, ext_net_id, router_create_args=None,
            network_create_args=None, subnet_create_args=None, **kwargs):
        router_create_args["name"] = self.generate_random_name()
        router_create_args.setdefault("external_gateway_info",
                                      {"network_id": ext_net_id, "enable_snat": True})
        router = self._create_router(router_create_args)

        network = self._create_network(network_create_args or {})
        subnet = self._create_subnet(network, subnet_create_args or {})
        self._add_interface_router(subnet['subnet'], router['router'])
        kwargs["nics"] = [{'net-id': network['network']['id']}]
        guest = self._boot_server_with_fip(image, flavor, True, None, **kwargs)

        self._wait_for_ping(guest[1]['ip'])

    @atomic.action_timer("neutron.create_router")
    def _create_router(self, router_create_args):
        """Create neutron router.

        :param router_create_args: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        return self.clients("neutron").create_router({"router": router_create_args})

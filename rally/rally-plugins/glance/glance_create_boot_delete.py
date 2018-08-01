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
from rally_openstack.scenarios.glance.images import GlanceBasic
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally_openstack.scenarios.nova import utils as nova_utils
from rally.task import scenario
from rally.task import types
from rally.task import validation


@types.convert(flavor={"type": "nova_flavor"}, image_location={"type": "path_or_url"})
@validation.add("required_services",
                services=[consts.Service.GLANCE, consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["glance", "neutron", "nova"]},
                    name="BrowbeatPlugin.glance_create_boot_delete",
                    platform="openstack")
class GlanceCreateBootDelete(GlanceBasic, neutron_utils.NeutronScenario, nova_utils.NovaScenario):

    def run(self, container_format, image_location, disk_format, flavor,
            network_create_args=None, subnet_create_args=None, **kwargs):
        image = self.glance.create_image(
            container_format=container_format, image_location=image_location,
            disk_format=disk_format)
        net = self._create_network(network_create_args or {})
        self._create_subnet(net, subnet_create_args or {})
        kwargs['nics'] = [{'net-id': net['network']['id']}]
        server = self._boot_server(image.id, flavor, **kwargs)
        self._delete_server(server)
        self.glance.delete_image(image.id)

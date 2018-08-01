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
from rally_openstack.scenarios.cinder import utils as cinder_utils
from rally_openstack.scenarios.nova import utils as nova_utils
from rally_openstack.scenarios.vm import utils as vm_utils
from rally.task import scenario
from rally.task import types
from rally.task import validation


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist", platform="openstack")
class NovaBootPersist(nova_utils.NovaScenario):

    def run(self, image, flavor, **kwargs):
        self._boot_server(image, flavor)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_volume",
                    platform="openstack")
class NovaBootPersistWithVolume(nova_utils.NovaScenario, cinder_utils.CinderBasic):

    def run(self, image, flavor, volume_size, **kwargs):
        server = self._boot_server(image, flavor)
        volume = self.cinder.create_volume(volume_size)
        self._attach_volume(server, volume)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay", "browbeat_persist_network"))
@validation.add("required_services",services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_network",
                    platform="openstack")
class NovaBootPersistWithNetwork(nova_utils.NovaScenario):

    def run(self, image, flavor, **kwargs):
        self._boot_server(image, flavor, **kwargs)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay", "browbeat_persist_network"))
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_network_volume",
                    platform="openstack")
class NovaBootPersistWithNetworkVolume(nova_utils.NovaScenario, cinder_utils.CinderBasic):

    def run(self, image, flavor, volume_size, **kwargs):
        server = self._boot_server(image, flavor, **kwargs)
        volume = self.cinder.create_volume(volume_size)
        self._attach_volume(server, volume)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_network_fip",
                    platform="openstack")
class NovaBootPersistWithNetworkFip(vm_utils.VMScenario):

    def run(self, image, flavor, external_net_name, boot_server_kwargs):
        server = self._boot_server(image, flavor, **boot_server_kwargs)
        self._attach_floating_ip(server, external_net_name)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_network_volume_fip",
                    platform="openstack")
class NovaBootPersistWithNetworkVolumeFip(vm_utils.VMScenario, cinder_utils.CinderBasic):

    def run(self, image, flavor, volume_size, boot_server_kwargs, external_net_name):
        server = self._boot_server(image, flavor, **boot_server_kwargs)
        volume = self.cinder.create_volume(volume_size)
        self._attach_volume(server, volume)
        self._attach_floating_ip(server, external_net_name)

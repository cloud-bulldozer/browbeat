
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
from rally.task import scenario
from rally.task import types
from rally.task import validation


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("restricted_parameters", param_names=["name", "display_name"],
                subdict="create_volume_params")
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder", "nova"]},
                    name="BrowbeatPlugin.create_vm_with_volume", platform="openstack")
class CreateVmWithVolume(cinder_utils.CinderBasic,
                         nova_utils.NovaScenario):

    def run(self, size, image, flavor, detailed=True,
            create_volume_params=None, create_vm_params=None, **kwargs):
        create_volume_params = create_volume_params or {}
        if kwargs and create_vm_params:
            raise ValueError("You can not set both 'kwargs' "
                             "and 'create_vm_params' attributes."
                             "Please use 'create_vm_params'.")

        create_vm_params = create_vm_params or kwargs or {}

        server = self._boot_server(image, flavor, **create_vm_params)
        volume = self.cinder.create_volume(size, **create_volume_params)

        self._attach_volume(server, volume)
        self._list_servers(detailed)
        self.cinder.list_volumes(detailed)

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
from rally.task import scenario
from rally.task import types
from rally.task import validation
import base


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add(
    "required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA]
)
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["neutron", "nova"]},
    name="BrowbeatPlugin.dynamic_workload",
    platform="openstack",
)
class DynamicWorkload(base.DynamicBase):
    def run(self, image, flavor, num_vms, subnet_create_args, **kwargs):
        self.create_delete_servers(image, flavor, num_vms, subnet_create_args=subnet_create_args)

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
import octavia


@types.convert(octavia_image={"type": "glance_image"}, octavia_flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="octavia_flavor", image_param="octavia_image")
@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add(
    "required_services", services=[consts.Service.NEUTRON,
                                   consts.Service.NOVA,
                                   consts.Service.OCTAVIA]
)
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={
        "cleanup@openstack": ["neutron", "nova", "octavia"],
        "keypair@openstack": {},
        "allow_ssh@openstack": None,
    },
    name="BrowbeatPlugin.dynamic_workload",
    platform="openstack",
)
class DynamicWorkload(base.DynamicBase, octavia.DynamicOctaviaBase):
    def run(
        self, image, flavor, ext_net_id, num_migrate_vms, jump_host_ip,
        user_data_file, num_lbs, num_pools, vip_subnet_id, num_clients,
        user, octavia_image, octavia_flavor, workloads="all", num_vms=1,
        router_create_args=None, network_create_args=None,
        subnet_create_args=None, **kwargs):

        if workloads != "all":
            workloads_list = workloads.split(",")

        if workloads == "all" or "create_delete_servers" in workloads_list:
            self.create_delete_servers(image, flavor, num_vms,
                                       subnet_create_args=subnet_create_args)

        if workloads == "all" or "migrate_servers" in workloads_list:
            self.server_boot_floatingip(image, flavor, ext_net_id, num_vms, router_create_args,
                                        network_create_args, subnet_create_args, **kwargs)
            self.migrate_servers_with_fip(num_migrate_vms)

        if "create_loadbalancers" in workloads_list:
            self.create_loadbalancers(octavia_image, octavia_flavor, user, num_lbs,
                                      jump_host_ip, vip_subnet_id, user_data_file, num_pools,
                                      num_clients, router_create_args, network_create_args,
                                      subnet_create_args, **kwargs)

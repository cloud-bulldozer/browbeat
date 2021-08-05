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
import vm
import trunk
import octavia


@types.convert(octavia_image={"type": "glance_image"}, octavia_flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="octavia_flavor", image_param="octavia_image")
@types.convert(trunk_image={"type": "glance_image"}, trunk_flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="trunk_flavor", image_param="trunk_image")
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
class DynamicWorkload(vm.VMDynamicScenario, trunk.TrunkDynamicScenario,
                      octavia.DynamicOctaviaBase):
    def run(
        self, image, flavor, ext_net_id, num_vms_to_create_for_migration,
        num_vms_to_migrate, user_data_file, user, num_lbs, num_pools,
        num_clients, octavia_image, octavia_flavor, trunk_image,
        trunk_flavor, num_initial_subports, num_trunk_vms,
        num_add_subports, num_add_subports_trunks,
        num_create_delete_vms, workloads="all",
        router_create_args=None,
        network_create_args=None,
        subnet_create_args=None,
        **kwargs):

        if workloads != "all":
            workloads_list = workloads.split(",")

        if workloads == "all" or "create_delete_servers" in workloads_list:
            self.create_delete_servers(image, flavor, num_create_delete_vms,
                                       subnet_create_args=subnet_create_args)

        if workloads == "all" or "migrate_servers" in workloads_list:
            self.boot_servers_with_fip(image, flavor, ext_net_id, num_vms_to_create_for_migration,
                                       router_create_args, network_create_args,
                                       subnet_create_args, **kwargs)
            self.migrate_servers_with_fip(num_vms_to_migrate)

        if workloads == "all" or "pod_fip_simulation" in workloads_list:
            self.pod_fip_simulation(ext_net_id, trunk_image, trunk_flavor,
                                    num_initial_subports, num_trunk_vms)

        if workloads == "all" or "add_subports_to_random_trunks" in workloads_list:
            self.add_subports_to_random_trunks(num_add_subports_trunks, num_add_subports)

        if "create_loadbalancers" in workloads_list:
            self.create_loadbalancers(octavia_image, octavia_flavor, user, num_lbs, user_data_file,
                                      num_pools, num_clients, ext_net_id, router_create_args,
                                      network_create_args, subnet_create_args, **kwargs)

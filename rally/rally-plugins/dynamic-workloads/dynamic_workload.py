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
import provider_network


@types.convert(octavia_image={"type": "glance_image"}, octavia_flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="octavia_flavor", image_param="octavia_image")
@types.convert(trunk_image={"type": "glance_image"}, trunk_flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="trunk_flavor", image_param="trunk_image")
@types.convert(smallest_image={"type": "glance_image"}, smallest_flavor={"type": "nova_flavor"})
@validation.add(
    "image_valid_on_flavor", flavor_param="smallest_flavor", image_param="smallest_image"
)
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
                      octavia.DynamicOctaviaBase, provider_network.DynamicProviderNetworkBase):
    def run(
        self, smallest_image, smallest_flavor, ext_net_id, num_vms_to_create_for_migration,
        num_vms_to_migrate, trunk_image, trunk_flavor, num_initial_subports, num_trunk_vms,
        num_add_subports, num_add_subports_trunks, num_delete_subports, num_delete_subports_trunks,
        octavia_image, octavia_flavor, user, user_data_file, num_lbs, num_pools, num_clients,
        delete_num_lbs, delete_num_members, num_create_delete_vms, provider_phys_net,
        iface_name, iface_mac, num_vms_provider_net, workloads="all",
        router_create_args=None, network_create_args=None,
        subnet_create_args=None, **kwargs):

        workloads_list = workloads.split(",")

        if workloads == "all" or "create_delete_servers" in workloads_list:
            self.create_delete_servers(smallest_image, smallest_flavor, num_create_delete_vms,
                                       subnet_create_args=subnet_create_args)

        if workloads == "all" or "migrate_servers" in workloads_list:
            self.boot_servers_with_fip(smallest_image, smallest_flavor, ext_net_id,
                                       num_vms_to_create_for_migration, router_create_args,
                                       network_create_args, subnet_create_args, **kwargs)
            self.migrate_servers_with_fip(num_vms_to_migrate)

        if workloads == "all" or "pod_fip_simulation" in workloads_list:
            self.pod_fip_simulation(ext_net_id, trunk_image, trunk_flavor, smallest_image,
                                    smallest_flavor, num_initial_subports, num_trunk_vms)

        if workloads == "all" or "add_subports_to_random_trunks" in workloads_list:
            self.add_subports_to_random_trunks(num_add_subports_trunks, num_add_subports)

        if workloads == "all" or "delete_subports_from_random_trunks" in workloads_list:
            self.delete_subports_from_random_trunks(num_delete_subports_trunks, num_delete_subports)

        if "create_loadbalancers" in workloads_list:
            self.create_loadbalancers(octavia_image, octavia_flavor, user, num_lbs, user_data_file,
                                      num_pools, num_clients, ext_net_id, router_create_args,
                                      network_create_args, subnet_create_args, **kwargs)

        if "delete_loadbalancers" in workloads_list:
            self.delete_loadbalancers(delete_num_lbs)

        if "delete_members_random_lb" in workloads_list:
            self.delete_members_random_lb(delete_num_members)

        if "provider_netcreate_nova_boot_ping" in workloads_list:
            self.provider_netcreate_nova_boot_ping(smallest_image, smallest_flavor,
                                                   provider_phys_net, iface_name,
                                                   iface_mac, num_vms_provider_net)

        if "provider_net_nova_boot_ping" in workloads_list:
            self.provider_net_nova_boot_ping(provider_phys_net, iface_name, iface_mac,
                                             smallest_image, smallest_flavor)

        if "provider_net_nova_delete" in workloads_list:
            self.provider_net_nova_delete(provider_phys_net)

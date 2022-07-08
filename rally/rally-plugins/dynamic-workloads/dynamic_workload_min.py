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

from rally_openstack.common import consts
from rally.task import scenario
from rally.task import types
from rally.task import validation
import vm


@types.convert(smallest_image={"type": "glance_image"}, smallest_flavor={"type": "nova_flavor"})
@validation.add(
    "image_valid_on_flavor", flavor_param="smallest_flavor", image_param="smallest_image"
)
@validation.add(
    "required_services", services=[consts.Service.NEUTRON,
                                   consts.Service.NOVA]
)
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={
        "cleanup@openstack": ["neutron", "nova"],
        "keypair@openstack": {},
        "allow_ssh@openstack": None,
    },
    name="BrowbeatPlugin.dynamic_workload_min",
    platform="openstack",
)
class DynamicWorkloadMin(vm.VMDynamicScenario):
    def run(
        self, smallest_image, smallest_flavor, ext_net_id, num_vms_to_create_with_fip,
        num_create_vms, num_vms_to_migrate, num_stop_start_vms, num_delete_vms,
        workloads="all", router_create_args=None, network_create_args=None,
        subnet_create_args=None, **kwargs):

        workloads_list = workloads.split(",")
        self.security_group = self.create_sec_group_with_icmp_ssh()
        self.log_info("security group {} created for this iteration".format(self.security_group))

        router_create_args["name"] = self.generate_random_name()
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault(
            "external_gateway_info", {"network_id": ext_net_id, "enable_snat": True}
        )
        self.router = self._create_router(router_create_args)
        self.log_info("router {} created for this iteration".format(self.router))

        self.keypair = self.context["user"]["keypair"]

        self.ext_net_name = self.clients("neutron").show_network(ext_net_id)["network"][
            "name"]

        if workloads == "all" or "create_delete_servers" in workloads_list:
            self.boot_servers(smallest_image, smallest_flavor, num_create_vms,
                              subnet_create_args=subnet_create_args)
            self.delete_random_servers(num_delete_vms)

        if(workloads == "all" or "migrate_servers" in workloads_list or
           "swap_floating_ips_between_servers" in workloads_list or
           "stop_start_servers" in workloads_list):
            self.boot_servers_with_fip(smallest_image, smallest_flavor, ext_net_id,
                                       num_vms_to_create_with_fip,
                                       network_create_args, subnet_create_args, **kwargs)

        if workloads == "all" or "migrate_servers" in workloads_list:
            self.migrate_servers_with_fip(num_vms_to_migrate)

        if workloads == "all" or "swap_floating_ips_between_servers" in workloads_list:
            self.swap_floating_ips_between_servers()

        if workloads == "all" or "stop_start_servers" in workloads_list:
            self.stop_start_servers_with_fip(num_stop_start_vms)

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

import os

from rally_openstack import consts
from rally.task import scenario
from rally.task import types
from rally.task import validation
import vm
import trunk
import octavia
import provider_network
import shift_on_stack


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
                      octavia.DynamicOctaviaBase, provider_network.DynamicProviderNetworkBase,
                      shift_on_stack.ShiftStackDynamicScenario):
    def run(
        self, smallest_image, smallest_flavor, ext_net_id, num_vms_to_create_with_fip,
        num_vms_to_migrate, num_stop_start_vms, trunk_image, trunk_flavor, num_initial_subports,
        num_trunk_vms, num_add_subports, num_add_subports_trunks, num_delete_subports,
        num_delete_subports_trunks, octavia_image, octavia_flavor, user, user_data_file, num_lbs,
        num_pools, num_clients, delete_num_lbs, delete_num_members, num_create_vms, num_delete_vms,
        provider_phys_net, iface_name, iface_mac, num_vms_provider_net, num_external_networks,
        shift_on_stack_job_iterations, shift_on_stack_qps, shift_on_stack_burst,
        shift_on_stack_workload, shift_on_stack_kubeconfig_paths, workloads="all",
        router_create_args=None, network_create_args=None,
        subnet_create_args=None, **kwargs):

        context_ext_net_id = self.context["external_networks"][((self.context["iteration"]-1)
                                                               % num_external_networks)]["id"]
        self.log_info("Using external network {} from context for iteration {}".format(
                      context_ext_net_id, self.context["iteration"]))

        workloads_list = workloads.split(",")
        self.trunk_vm_user = "centos"
        self.jumphost_user = "cirros"

        # Let this security group to be used by resources created in this iteration.
        # _boot_server_with_tag additionally add's tenant/user's default security group
        # for the resources created in every 5th iteration for scale testing of decurity groups
        self.security_group = self.create_sec_group_with_icmp_ssh()
        self.log_info("security group {} created for this iteration".format(self.security_group))

        # Let this router be used by resources created by VM dynamic workloads in this iteration,
        # if the iteration is not divisible by 5.
        router_create_args["name"] = self.generate_random_name()
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault(
            "external_gateway_info", {"network_id": context_ext_net_id, "enable_snat": True}
        )
        self.router = self._create_router(router_create_args)
        self.log_info("router {} created for this iteration".format(self.router))

        self.keypair = self.context["user"]["keypair"]

        self.ext_net_name = self.clients("neutron").show_network(context_ext_net_id)["network"][
            "name"]

        try:
            self.browbeat_dir = DynamicWorkload.browbeat_dir
        except AttributeError:
            DynamicWorkload.browbeat_dir = os.getcwd()

        if workloads == "all" or "create_delete_servers" in workloads_list:
            self.boot_servers(smallest_image, smallest_flavor, num_create_vms,
                              subnet_create_args=subnet_create_args)
            self.delete_random_servers(num_delete_vms)

        if(workloads == "all" or "migrate_servers" in workloads_list or
           "swap_floating_ips_between_servers" in workloads_list or
           "stop_start_servers" in workloads_list):
            if self.context["iteration"] % 5 != 0:
                self.boot_servers_with_fip(smallest_image, smallest_flavor, context_ext_net_id,
                                           num_vms_to_create_with_fip,
                                           network_create_args, subnet_create_args, **kwargs)
            else:
                # Every 5th iteration uses the router from rally context, which uses
                # the default external network provided in browbeat-config.yaml as
                # gateway. So we pass this default external network as a parameter
                # for every 5th iteration.
                self.boot_servers_with_fip(smallest_image, smallest_flavor, ext_net_id,
                                           num_vms_to_create_with_fip,
                                           network_create_args, subnet_create_args, **kwargs)

        if workloads == "all" or "migrate_servers" in workloads_list:
            self.migrate_servers_with_fip(num_vms_to_migrate)

        if workloads == "all" or "swap_floating_ips_between_servers" in workloads_list:
            self.swap_floating_ips_between_servers()

        if workloads == "all" or "stop_start_servers" in workloads_list:
            self.stop_start_servers_with_fip(num_stop_start_vms)

        if workloads == "all" or "pod_fip_simulation" in workloads_list:
            self.pod_fip_simulation(context_ext_net_id, trunk_image, trunk_flavor, smallest_image,
                                    smallest_flavor, num_initial_subports, num_trunk_vms)

        if workloads == "all" or "add_subports_to_random_trunks" in workloads_list:
            self.add_subports_to_random_trunks(num_add_subports_trunks, num_add_subports)

        if workloads == "all" or "delete_subports_from_random_trunks" in workloads_list:
            self.delete_subports_from_random_trunks(num_delete_subports_trunks, num_delete_subports)

        if workloads == "all" or "swap_floating_ips_between_random_subports" in workloads_list:
            self.swap_floating_ips_between_random_subports()

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

        if "shift_on_stack" in workloads_list:
            num_openshift_clusters = len(shift_on_stack_kubeconfig_paths)
            self.run_kube_burner_workload(shift_on_stack_workload,
                                          shift_on_stack_job_iterations,
                                          shift_on_stack_qps, shift_on_stack_burst,
                                          shift_on_stack_kubeconfig_paths[
                                              ((self.context["iteration"] - 1)
                                               % num_openshift_clusters)])

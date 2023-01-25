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

import logging
import time
from rally_openstack.common import consts
from rally_openstack.task.scenarios.cinder import utils as cinder_utils
from rally_openstack.task.scenarios.nova import utils as nova_utils
from rally_openstack.task.scenarios.neutron import utils as neutron_utils
from rally_openstack.task.scenarios.vm import utils as vm_utils
from rally.task import scenario
from rally.task import types
from rally.task import validation

from rally_openstack.common.services.network import neutron
from rally_openstack.common import osclients

LOG = logging.getLogger(__name__)

@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist", platform="openstack")
class NovaBootPersist(nova_utils.NovaScenario):

    def run(self, image, flavor, **kwargs):
        self._boot_server(image, flavor)

@types.convert(image={"type": "glance_image"}, vanilla_flavor={"type": "nova_flavor"},
               dpdk_flavor={"type": "nova_flavor"}, hw_offload_flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="vanilla_flavor", image_param="image")
@validation.add("image_valid_on_flavor", flavor_param="dpdk_flavor", image_param="image")
@validation.add("image_valid_on_flavor", flavor_param="hw_offload_flavor", image_param="image")
@validation.add("required_contexts", contexts=("create_nfv_azs_and_networks"))
@validation.add("required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"]},
                    name="BrowbeatNova.nova_boot_hybrid_computes", platform="openstack")
class NovaBootHybridComputes(nova_utils.NovaScenario, neutron_utils.NeutronScenario):

    def run(self, image, vanilla_flavor, dpdk_flavor,
            hw_offload_flavor, num_networks_per_tenant,
            dpdk_management_nw_type, hw_offload_management_nw_type,
            proportional_scale, **kwargs):
        """Create VMs on non-NFV compute nodes, SR-IOV+DPDK compute nodes,
           and SR-IOV+Hardware Offload compute nodes.
        :param image: image ID or instance for server creation
        :param vanilla_flavor: flavor ID or instance for server creation
        :param dpdk_flavor: flavor ID or instance for SR-IOV+DPDK VM creation
        :param hw_offload_flavor: flavor ID or instance for SR-IOV+Hardware Offload VM creation
        :param num_networks_per_tenant: int, number of tunnel networks per tenant
        :param dpdk_management_nw_type: str, management network for DPDK VMs
        :param hw_offload_management_nw_type: str, management network for HW Offload VMs
        :param proportional_scale: str, option to scale VMs proportionately
        """
        tenant_id = self.context["tenant"]["id"]
        minimum_num_compute_hosts = min(self.context["num_vanilla_compute_hosts"],
                                        self.context.get("num_dpdk_compute_hosts",
                                                         self.context[
                                                             "num_vanilla_compute_hosts"]),
                                        self.context.get("num_hw_offload_compute_hosts",
                                                         self.context[
                                                             "num_vanilla_compute_hosts"]))

        vanilla_provider_network = self.context["vanilla_networks"][tenant_id]
        tenant_network_id = self.context["tenant"]["networks"][((self.context["iteration"]-1)
                                                               % num_networks_per_tenant)]["id"]
        LOG.info("ITER {} using tenant network {}".format(self.context["iteration"],
                                                          tenant_network_id))
        kwargs["nics"] = [{'net-id': vanilla_provider_network["id"]}]
        kwargs["availability-zone"] = "az_vanilla_compute"

        proportional_scale = proportional_scale in ["True", "true"]
        if proportional_scale:
            num_vanilla_vms_to_boot = self.context[
                "num_vanilla_compute_hosts"] // minimum_num_compute_hosts
            if self.context["boot_dpdk_vms"]:
                num_dpdk_vms_to_boot = self.context[
                    "num_dpdk_compute_hosts"] // minimum_num_compute_hosts
            if self.context["boot_hw_offload_vms"]:
                num_sriov_hw_offload_vms_to_boot = self.context[
                    "num_hw_offload_compute_hosts"] // minimum_num_compute_hosts
        else:
            num_vanilla_vms_to_boot = 1
            if self.context["boot_dpdk_vms"]:
                num_dpdk_vms_to_boot = 1
            if self.context["boot_hw_offload_vms"]:
                num_sriov_hw_offload_vms_to_boot = 1

        for _ in range(num_vanilla_vms_to_boot):
            vanilla_server = self._boot_server(image, vanilla_flavor, **kwargs)
            self._attach_interface(vanilla_server, net_id=tenant_network_id)
            LOG.info("ITER {} Booted vanilla server : {}".format(self.context["iteration"],
                                                                 vanilla_server.id))
            # VMs booting simultaneously across iterations adds a lot of load, so delay booting VMs
            # for 5 seconds.
            time.sleep(5)

        if self.context["boot_dpdk_vms"]:
            LOG.info("ITER {} DPDK instances enabled.".format(self.context["iteration"]))

            dpdk_server_kwargs = {}
            dpdk_networks = self.context["nfv_networks"]["dpdk"]

            if dpdk_management_nw_type == "sriov":
                sriov_port_kwargs = {}
                sriov_networks = self.context["nfv_networks"]["sriov"]
                sriov_network = sriov_networks[tenant_id]
                sriov_port_kwargs["binding:vnic_type"] = "direct"

            for _ in range(num_dpdk_vms_to_boot):
                if dpdk_management_nw_type == "sriov":
                    sriov_port = self._create_port({"network": sriov_network}, sriov_port_kwargs)
                    dpdk_server_kwargs["nics"] = [{'port-id': sriov_port["port"]["id"]},
                                                  {'net-id': dpdk_networks[tenant_id]["id"]}]
                elif dpdk_management_nw_type == "tenant":
                    dpdk_server_kwargs["nics"] = [{'net-id': tenant_network_id},
                                                  {'net-id': dpdk_networks[tenant_id]["id"]}]
                else:
                    raise Exception("{} is not a valid management network type. {}".format(
                                    dpdk_management_nw_type, "Please choose sriov or tenant."))
                dpdk_server_kwargs["availability-zone"] = "az_dpdk"
                dpdk_server = self._boot_server(image, dpdk_flavor,
                                                **dpdk_server_kwargs)
                LOG.info("ITER {} Booted DPDK server : {}".format(self.context["iteration"],
                                                                  dpdk_server.id))
                # VMs booting simultaneously across iterations adds a lot of load,
                # so delay booting VMs for 5 seconds.
                time.sleep(5)

        if self.context["boot_hw_offload_vms"]:
            LOG.info("ITER {} Hardware Offload Instances enabled.".format(
                     self.context["iteration"]))

            hw_offload_server_kwargs = {}
            hw_offload_network = self.context["nfv_networks"]["hw_offload"][tenant_id]
            hw_offload_subnet = self.context["nfv_subnets"]["hw_offload"][tenant_id]

            if hw_offload_management_nw_type == "sriov":
                sriov_networks = self.context["nfv_networks"]["sriov"]
                sriov_network = sriov_networks[tenant_id]
                sriov_port_kwargs = {}
                sriov_port_kwargs["binding:vnic_type"] = "direct"

            admin_clients = osclients.Clients(self.context["admin"]["credential"])
            self.admin_neutron = neutron.NeutronService(
                clients=admin_clients,
                name_generator=self.generate_random_name,
                atomic_inst=self.atomic_actions()
            )

            hw_offload_port_kwargs = {}
            hw_offload_port_kwargs["binding:vnic_type"] = "direct"
            hw_offload_port_kwargs["fixed_ips"] = [{"subnet_id": hw_offload_subnet["id"]}]

            for _ in range(num_sriov_hw_offload_vms_to_boot):
                if hw_offload_management_nw_type == "sriov":
                    sriov_port = self._create_port({"network": sriov_network}, sriov_port_kwargs)
                hw_offload_port = self._create_port({"network": hw_offload_network},
                                                    hw_offload_port_kwargs)

                hw_offload_port_kwargs["binding:profile"] = {"capabilities": ["switchdev"]}
                hw_offload_port = {"port": self.admin_neutron.update_port(
                                   port_id=hw_offload_port["port"]["id"],
                                   **hw_offload_port_kwargs)}

                if hw_offload_management_nw_type == "sriov":
                    hw_offload_server_kwargs["nics"] = [{'port-id': sriov_port["port"]["id"]},
                                                        {'port-id':
                                                            hw_offload_port["port"]["id"]}]
                elif hw_offload_management_nw_type == "tenant":
                    hw_offload_server_kwargs["nics"] = [{'net-id': tenant_network_id},
                                                        {'port-id':
                                                            hw_offload_port["port"]["id"]}]
                else:
                    raise Exception("{} is not a valid management network type. {}".format(
                                    hw_offload_management_nw_type,
                                    "Please choose sriov or tenant."))

                hw_offload_server_kwargs["availability-zone"] = "az_hw_offload"
                hw_offload_server = self._boot_server(image, hw_offload_flavor,
                                                      **hw_offload_server_kwargs)
                LOG.info("ITER {} Booted Hardware Offload server : {}".format(
                         self.context["iteration"], hw_offload_server.id))

                # VMs booting simultaneously across iterations adds a lot of load,
                # so delay booting VMs for 5 seconds.
                time.sleep(5)

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

@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"]},
                    name="BrowbeatNova.nova_boot_in_batches_with_delay",
                    platform="openstack")
class NovaBootInBatchesWithDelay(vm_utils.VMScenario):

    def run(self, image, flavor, delay_time, iterations_per_batch,
            num_iterations_to_delay, num_networks_per_tenant, concurrency, **kwargs):
        """Boot VMs in batches with delay in between. This scenario is useful for scaling VMs incrementally.
        :param image: image of the VMs to be booted
        :param flavor: flavor of the VMs to be booted
        :param delay_time: int, time in seconds to delay VM boot in between batches
        :param iterations_per_batch: int, number of iterations that can run before delay occurs
        :param num_iterations_to_delay: int, number of iterations to delay
        :param num_networks_per_tenant: int, number of tenant networks
        :param concurrency: int, concurrency passed to rally runner
        """
        if iterations_per_batch <= num_iterations_to_delay:
            raise Exception("num_iterations_to_delay cannot be greater than iterations_per_batch.")
        if iterations_per_batch <= concurrency:
            raise Exception("concurrency cannot be greater than iterations_per_batch.")
        if (self.context["iteration"] % iterations_per_batch <= num_iterations_to_delay and
           self.context["iteration"] >= iterations_per_batch):
            LOG.info("Iteration {} delaying VM boot for {} seconds".format(
                     self.context["iteration"], delay_time))
            time.sleep(delay_time)
        tenant_network_id = self.context["tenant"]["networks"][((self.context["iteration"]-1)
                                                               % num_networks_per_tenant)]["id"]
        LOG.info("Iteration {} using tenant network {}".format(self.context["iteration"],
                                                               tenant_network_id))
        kwargs["nics"] = [{"net-id": tenant_network_id}]
        self._boot_server(image, flavor, **kwargs)

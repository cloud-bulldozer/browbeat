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

from rally.task import context
from rally.common import logging
from rally.common import utils
from rally import consts
from rally_openstack.common import osclients
from rally_openstack.common.wrappers import network as network_wrapper

import yaml

LOG = logging.getLogger(__name__)


@context.configure(name="create_nfv_azs_and_networks", order=1100)
class CreateNFVAZsandNetworksContext(context.Context):
    """This plugin creates availability zones with host aggregates and networks
    for non-NFV, SR-IOV with DPDK and SR-IOV with hardware offload.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "additionalProperties": True,
        "properties": {
            "boot_dpdk_vms": {
                "type": "string",
                "default": "False"
            },
            "boot_hw_offload_vms": {
                "type": "string",
                "default": "False"
            },
            "dpdk_hosts_group": {
                "type": "string",
                "default": "ComputeOvsDpdkSriov"
            },
            "hw_offload_hosts_group": {
                "type": "string",
                "default": "ComputeSriovOffload"
            },
            "tripleo_inventory_file": {
                "type": "string",
                "default": "/home/stack/browbeat/ansible/hosts.yml"
            }
        }
    }

    def _create_subnet(self, tenant_id, network_id, network_number):
        """Create subnet for network

        :param tenant_id: ID of tenant
        :param network_id: ID of network
        :param network_number: int, number for CIDR of subnet
        :returns: subnet object
        """
        subnet_args = {
            "subnet": {
                "tenant_id": tenant_id,
                "network_id": network_id,
                "name": self.net_wrapper.owner.generate_random_name(),
                "ip_version": 4,
                "cidr": "172.{}.0.0/16".format(network_number),
                "enable_dhcp": True,
                "gateway_ip": "172.{}.0.1".format(network_number),
                "allocation_pools": [{"start": "172.{}.0.2".format(network_number),
                                      "end": "172.{}.254.254".format(network_number)}]
            }
        }
        return self.net_wrapper.client.create_subnet(subnet_args)["subnet"]

    def _create_networks_and_subnets(self, tenant_id):
        self.net_wrapper = network_wrapper.wrap(
            osclients.Clients(self.context["admin"]["credential"]),
            self,
            config=self.config,
        )

        net_kwargs = {
            "network_create_args": {
                "provider:network_type": "vlan",
                "provider:physical_network": self.config["provider_phys_nets"]["vanilla"],
                "provider:segmentation_id": self.network_vlan_number,
            }
        }
        vanilla_network = self.net_wrapper.create_network(tenant_id, **net_kwargs)

        self.context["vanilla_networks"][tenant_id] = vanilla_network
        self.context["vanilla_subnets"][tenant_id] = self._create_subnet(
            tenant_id, vanilla_network["id"],
            self.network_vlan_number-950)
        self.network_vlan_number += 1

        if self.context["boot_dpdk_vms"]:
            net_kwargs = {
                "network_create_args": {
                    "provider:network_type": "vlan",
                    "provider:physical_network": self.config["provider_phys_nets"]["dpdk"],
                    "provider:segmentation_id": self.network_vlan_number,
                }
            }

            dpdk_network = self.net_wrapper.create_network(tenant_id, **net_kwargs)
            self.context["nfv_networks"].setdefault("dpdk", {})
            self.context["nfv_networks"]["dpdk"][tenant_id] = dpdk_network
            self.context["nfv_subnets"].setdefault("dpdk", {})
            self.context["nfv_subnets"]["dpdk"][tenant_id] = self._create_subnet(
                tenant_id, dpdk_network["id"],
                self.network_vlan_number-950)
            self.network_vlan_number += 1

            net_kwargs = {
                "network_create_args": {
                    "provider:network_type": "vlan",
                    "provider:physical_network": self.config["provider_phys_nets"]["sriov"],
                    "provider:segmentation_id": self.network_vlan_number,
                }
            }
            sriov_network = self.net_wrapper.create_network(tenant_id, **net_kwargs)

            self.context["nfv_networks"].setdefault("sriov", {})
            self.context["nfv_networks"]["sriov"][tenant_id] = sriov_network
            self.context["nfv_subnets"].setdefault("sriov", {})
            self.context["nfv_subnets"]["sriov"][tenant_id] = self._create_subnet(
                tenant_id, sriov_network["id"],
                self.network_vlan_number-950)
            self.network_vlan_number += 1

        if self.context["boot_hw_offload_vms"]:
            net_kwargs = {
                "network_create_args": {
                    "provider:network_type": "vlan",
                    "provider:physical_network": self.config["provider_phys_nets"]["hw_offload"],
                    "provider:segmentation_id": self.network_vlan_number,
                }
            }
            hw_offload_network = self.net_wrapper.create_network(tenant_id, **net_kwargs)

            self.context["nfv_networks"].setdefault("hw_offload", {})
            self.context["nfv_networks"]["hw_offload"][tenant_id] = hw_offload_network
            self.context["nfv_subnets"].setdefault("hw_offload", {})
            self.context["nfv_subnets"]["hw_offload"][tenant_id] = self._create_subnet(
                tenant_id, hw_offload_network["id"],
                self.network_vlan_number-950)
            self.network_vlan_number += 1

    def setup(self):
        """This method is called before the task starts."""
        self.net_wrapper = network_wrapper.wrap(
            osclients.Clients(self.context["admin"]["credential"]),
            self,
            config=self.config,
        )
        self.nova_wrapper = osclients.Nova(self.context["admin"]["credential"]).create_client()
        self.context["nfv_networks"] = {}
        self.context["nfv_subnets"] = {}
        self.context["vanilla_networks"] = {}
        self.context["vanilla_subnets"] = {}
        # This has been made a string value so that upper case/lower case
        # variations can be considered.
        self.context["boot_dpdk_vms"] = self.config.get("boot_dpdk_vms", "False") in [
            "True", "true"]
        self.context["boot_hw_offload_vms"] = self.config.get("boot_hw_offload_vms",
                                                              "False") in [
                                                                  "True", "true"]
        self.dpdk_hosts_group = self.config.get("dpdk_hosts_group",
                                                "ComputeOvsDpdk")
        self.hw_offload_hosts_group = self.config.get("hw_offload_hosts_group",
                                                      "ComputeSriovOffload")
        self.network_vlan_number = 1001

        tripleo_inventory_file_path = self.config.get("tripleo_inventory_file",
                                                      "/home/stack/browbeat/ansible/hosts.yml")
        with open(tripleo_inventory_file_path, "r") as tripleo_inventory_file:
            self.tripleo_inventory = yaml.safe_load(tripleo_inventory_file)

        dpdk_and_hw_offload_hosts = []

        if self.context["boot_dpdk_vms"]:
            self.dpdk_aggregate = self.nova_wrapper.aggregates.create(
                "dpdk_aggregate", "az_dpdk")
            dpdk_hosts = self.tripleo_inventory[self.dpdk_hosts_group]["hosts"]
            self.context["num_dpdk_compute_hosts"] = len(dpdk_hosts)
            for host_details in dpdk_hosts.values():
                self.nova_wrapper.aggregates.add_host(self.dpdk_aggregate.id,
                                                      host_details["canonical_hostname"])
                dpdk_and_hw_offload_hosts.append(host_details["canonical_hostname"])

        if self.context["boot_hw_offload_vms"]:
            self.hw_offload_aggregate = self.nova_wrapper.aggregates.create(
                "hw_offload_aggregate", "az_hw_offload")
            hw_offload_hosts = self.tripleo_inventory[
                self.hw_offload_hosts_group]["hosts"]
            self.context["num_hw_offload_compute_hosts"] = len(hw_offload_hosts)
            for host_details in hw_offload_hosts.values():
                self.nova_wrapper.aggregates.add_host(self.hw_offload_aggregate.id,
                                                      host_details["canonical_hostname"])
                dpdk_and_hw_offload_hosts.append(host_details["canonical_hostname"])

        self.vanilla_compute_aggregate = self.nova_wrapper.aggregates.create(
            "vanilla_compute_aggregate", "az_vanilla_compute")

        self.vanilla_compute_hosts = set()
        for hostsgroup in self.tripleo_inventory:
            if "hosts" in self.tripleo_inventory[hostsgroup] and "Compute" in hostsgroup:
                for host_details in self.tripleo_inventory[hostsgroup]["hosts"].values():
                    if ("canonical_hostname" in host_details and
                       host_details["canonical_hostname"] not in dpdk_and_hw_offload_hosts):
                        self.nova_wrapper.aggregates.add_host(
                            self.vanilla_compute_aggregate.id,
                            host_details["canonical_hostname"])
                        self.vanilla_compute_hosts.add(host_details["canonical_hostname"])
        self.context["num_vanilla_compute_hosts"] = len(self.vanilla_compute_hosts)

        for _, tenant_id in utils.iterate_per_tenants(
            self.context.get("users", [])
        ):
            self._create_networks_and_subnets(tenant_id)

    def cleanup(self):
        """This method is called after the task finishes."""
        for hostname in self.vanilla_compute_hosts:
            self.nova_wrapper.aggregates.remove_host(self.vanilla_compute_aggregate.id,
                                                     hostname)
        self.nova_wrapper.aggregates.delete(self.vanilla_compute_aggregate.id)

        if self.context["boot_dpdk_vms"]:
            dpdk_hosts = self.tripleo_inventory[self.dpdk_hosts_group]["hosts"]
            for host_details in dpdk_hosts.values():
                self.nova_wrapper.aggregates.remove_host(self.dpdk_aggregate.id,
                                                         host_details["canonical_hostname"])
            self.nova_wrapper.aggregates.delete(self.dpdk_aggregate.id)

        if self.context["boot_hw_offload_vms"]:
            hw_offload_hosts = self.tripleo_inventory[
                self.hw_offload_hosts_group]["hosts"]
            for host_details in hw_offload_hosts.values():
                self.nova_wrapper.aggregates.remove_host(self.hw_offload_aggregate.id,
                                                         host_details["canonical_hostname"])
            self.nova_wrapper.aggregates.delete(self.hw_offload_aggregate.id)

        for subnet in self.context["vanilla_subnets"].values():
            try:
                subnet_id = subnet["id"]
                self.net_wrapper._delete_subnet(subnet_id)
                LOG.debug(
                    "Subnet with id '%s' deleted from context"
                    % subnet_id
                )
            except Exception as e:
                msg = "Can't delete subnet {} from context: {}".format(
                    subnet_id, e
                )
                LOG.warning(msg)

        for network in self.context["vanilla_networks"].values():
            try:
                network_id = network["id"]
                self.net_wrapper.delete_network(network)
                LOG.debug(
                    "Network with id '%s' deleted from context"
                    % network_id
                )
            except Exception as e:
                msg = "Can't delete network {} from context: {}".format(
                    network_id, e
                )
                LOG.warning(msg)

        for subnets in self.context["nfv_subnets"].values():
            for subnet in subnets.values():
                try:
                    nfv_subnet_id = subnet["id"]
                    self.net_wrapper._delete_subnet(nfv_subnet_id)
                    LOG.debug(
                        "Subnet with id '%s' deleted from context"
                        % nfv_subnet_id
                    )
                except Exception as e:
                    msg = "Can't delete subnet {} from context: {}".format(
                        nfv_subnet_id, e
                    )
                    LOG.warning(msg)

        for networks in self.context["nfv_networks"].values():
            for network in networks.values():
                try:
                    nfv_network_id = network["id"]
                    self.net_wrapper.delete_network(network)
                    LOG.debug(
                        "Network with id '%s' deleted from context"
                        % nfv_network_id
                    )
                except Exception as e:
                    msg = "Can't delete network {} from context: {}".format(
                        nfv_network_id, e
                    )
                    LOG.warning(msg)

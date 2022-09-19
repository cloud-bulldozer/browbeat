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
from rally_openstack import osclients
from rally_openstack.wrappers import network as network_wrapper

LOG = logging.getLogger(__name__)


@context.configure(name="create_provider_networks", order=1000)
class CreateProviderNetworksContext(context.Context):
    """This plugin creates provider networks with specified option."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "additionalProperties": False,
        "properties": {
            "num_provider_networks": {
                "type": "integer",
                "minimum": 0
            },
            "iface_name": {
                "type": "string"
            },
            "iface_mac": {
                "type": "string"
            },
            "provider_phys_net": {
                "type": "string"
            },
            "cidr_prefix": {
                "type": "string"
            }
        }
    }

    def _create_subnet(self, tenant_id, network_id, network_number):
        """Create subnet for provider network

        :param tenant_id: ID of tenant
        :param network_id: ID of provider network
        :param network_number: int, number for CIDR of subnet
        :returns: subnet object
        """
        subnet_args = {
            "subnet": {
                "tenant_id": tenant_id,
                "network_id": network_id,
                "name": self.net_wrapper.owner.generate_random_name(),
                "ip_version": 4,
                "cidr": "{}.{}.0/23".format(self.cidr_prefix, network_number),
                "gateway_ip": "{}.{}.1".format(self.cidr_prefix, network_number),
                "allocation_pools": [{"start": "{}.{}.2".format(self.cidr_prefix, network_number),
                                      "end": "{}.{}.254".format(
                                      self.cidr_prefix, network_number+1)}]
            }
        }
        return self.net_wrapper.client.create_subnet(subnet_args)["subnet"]

    def setup(self):
        """This method is called before the task starts."""
        self.net_wrapper = network_wrapper.wrap(
            osclients.Clients(self.context["admin"]["credential"]),
            self,
            config=self.config,
        )
        self.context["provider_networks"] = []
        self.context["provider_subnets"] = {}
        self.num_provider_networks = self.config.get("num_provider_networks", 16)
        self.context["iface_name"] = self.config.get("iface_name", "ens7f0")
        self.context["iface_mac"] = self.config.get("iface_mac", " ")
        self.provider_phys_net = self.config.get("provider_phys_net", "datacentre")
        self.cidr_prefix = self.config.get("cidr_prefix", "172.31")
        num_provider_networks_created = 0

        while num_provider_networks_created < self.num_provider_networks:
            has_error_occured = False
            for user, tenant_id in utils.iterate_per_tenants(
                self.context.get("users", [])
            ):
                try:
                    kwargs = {
                        "network_create_args": {
                            "provider:network_type": "vlan",
                            "provider:physical_network": self.provider_phys_net
                        }
                    }
                    self.context["provider_networks"].append(
                        self.net_wrapper.create_network(tenant_id, **kwargs)
                    )
                    LOG.debug(
                        "Provider network with id '%s' created as part of context"
                        % self.context["provider_networks"][-1]["id"]
                    )
                    num_provider_networks_created += 1
                except Exception as e:
                    msg = "Can't create provider network {} as part of context: {}".format(
                        num_provider_networks_created, e
                    )
                    LOG.exception(msg)
                    has_error_occured = True
                    break

                try:
                    subnet = self._create_subnet(tenant_id,
                                                 self.context["provider_networks"][-1]["id"],
                                                 (num_provider_networks_created - 1) * 2)
                    self.context["provider_subnets"][
                        self.context["provider_networks"][-1]["id"]] = subnet
                    LOG.debug(
                        "Provider subnet with id '%s' created as part of context"
                        % subnet["id"]
                    )
                except Exception as e:
                    msg = "Can't create provider subnet {} as part of context: {}".format(
                        num_provider_networks_created, e
                    )
                    LOG.exception(msg)
                    has_error_occured = True
                    break

            if has_error_occured:
                break

    def cleanup(self):
        """This method is called after the task finishes."""
        for i in range(self.num_provider_networks):
            try:
                provider_net = self.context["provider_networks"][i]
                provider_net_id = provider_net["id"]
                provider_subnet = self.context["provider_subnets"][provider_net_id]
                provider_subnet_id = provider_subnet["id"]
                self.net_wrapper._delete_subnet(provider_subnet_id)
                LOG.debug(
                    "Provider subnet with id '%s' deleted from context"
                    % provider_subnet_id
                )
                self.net_wrapper.delete_network(provider_net)
                LOG.debug(
                    "Provider network with id '%s' deleted from context"
                    % provider_net_id
                )
            except Exception as e:
                msg = "Can't delete provider network {} from context: {}".format(
                    provider_net_id, e
                )
                LOG.warning(msg)

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

import subprocess

LOG = logging.getLogger(__name__)


@context.configure(name="create_external_networks", order=1000)
class CreateExternalNetworksContext(context.Context):
    """This plugin creates external networks with specified option."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "additionalProperties": False,
        "properties": {
            "num_external_networks": {
                "type": "integer",
                "minimum": 0
            },
            "interface_name": {
                "type": "string"
            },
            "provider_phys_net": {
                "type": "string"
            }
        }
    }

    def _create_subnet(self, tenant_id, network_id, network_number):
        """Create subnet for external network

        :param tenant_id: ID of tenant
        :param network_id: ID of external network
        :param network_number: int, number for CIDR of subnet
        :returns: subnet object
        """
        subnet_args = {
            "subnet": {
                "tenant_id": tenant_id,
                "network_id": network_id,
                "name": self.net_wrapper.owner.generate_random_name(),
                "ip_version": 4,
                "cidr": "172.31.{}.0/23".format(network_number),
                "enable_dhcp": False,
                "gateway_ip": "172.31.{}.1".format(network_number),
                "allocation_pools": [{"start": "172.31.{}.2".format(network_number),
                                      "end": "172.31.{}.254".format(network_number+1)}]
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
        self.context["external_networks"] = []
        self.context["external_subnets"] = {}
        self.num_external_networks = self.config.get("num_external_networks", 16)
        self.interface_name = self.config.get("interface_name", "ens7f1")

        num_external_networks_created = 0

        while num_external_networks_created < self.num_external_networks:
            has_error_occured = False
            for user, tenant_id in utils.iterate_per_tenants(
                self.context.get("users", [])
            ):
                cmd = ["sudo", "ip", "link", "add", "link", self.interface_name, "name",
                       "{}.{}".format(self.interface_name, num_external_networks_created + 1),
                       "type", "vlan", "id", str(num_external_networks_created + 1)]
                proc = subprocess.Popen(cmd)
                proc.wait()
                if proc.returncode == 0:
                    LOG.debug("Creating vlan {} on interface {} was successful".format(
                              num_external_networks_created + 1, self.interface_name))
                else:
                    LOG.exception("Creating vlan {} on interface {} failed".format(
                                  num_external_networks_created + 1, self.interface_name))
                    has_error_occured = True
                    break

                cmd = ["sudo", "ip", "link", "set", "dev",
                       "{}.{}".format(self.interface_name, num_external_networks_created + 1),
                       "up"]
                proc = subprocess.Popen(cmd)
                proc.wait()
                if proc.returncode == 0:
                    LOG.debug("Setting vlan {} up on interface {} was successful".format(
                              num_external_networks_created + 1, self.interface_name))
                else:
                    LOG.exception("Setting vlan {} up on interface {} failed".format(
                                  num_external_networks_created + 1, self.interface_name))
                    has_error_occured = True
                    break

                cmd = ["sudo", "ip", "a", "a", "172.31.{}.1/23".format(
                       num_external_networks_created*2), "dev",
                       "{}.{}".format(self.interface_name, num_external_networks_created + 1)]
                proc = subprocess.Popen(cmd)
                proc.wait()
                if proc.returncode == 0:
                    LOG.debug("Adding IP range to interface {} was successful".format(
                              self.interface_name))
                else:
                    LOG.exception("Adding IP range to interface {} failed".format(
                                  self.interface_name))
                    has_error_occured = True
                    break

                try:
                    kwargs = {
                        "network_create_args": {
                            "provider:network_type": "vlan",
                            "provider:physical_network": self.config.get("provider_phys_net",
                                                                         "datacentre"),
                            "provider:segmentation_id": num_external_networks_created + 1,
                            "router:external": True
                        }
                    }
                    self.context["external_networks"].append(
                        self.net_wrapper.create_network(tenant_id, **kwargs)
                    )
                    LOG.debug(
                        "External network with id '%s' created as part of context"
                        % self.context["external_networks"][-1]["id"]
                    )
                    num_external_networks_created += 1
                except Exception as e:
                    msg = "Can't create external network {} as part of context: {}".format(
                        num_external_networks_created, e
                    )
                    LOG.exception(msg)
                    has_error_occured = True
                    break

                try:
                    subnet = self._create_subnet(tenant_id,
                                                 self.context["external_networks"][-1]["id"],
                                                 (num_external_networks_created - 1) * 2)
                    self.context["external_subnets"][
                        self.context["external_networks"][-1]["id"]] = subnet
                    LOG.debug(
                        "External subnet with id '%s' created as part of context"
                        % subnet["id"]
                    )
                except Exception as e:
                    msg = "Can't create external subnet {} as part of context: {}".format(
                        num_external_networks_created, e
                    )
                    LOG.exception(msg)
                    has_error_occured = True
                    break

            if has_error_occured:
                break

    def cleanup(self):
        """This method is called after the task finishes."""
        for i in range(self.num_external_networks):
            try:
                external_net = self.context["external_networks"][i]
                external_net_id = external_net["id"]
                external_subnet = self.context["external_subnets"][external_net_id]
                external_subnet_id = external_subnet["id"]
                self.net_wrapper._delete_subnet(external_subnet_id)
                LOG.debug(
                    "External subnet with id '%s' deleted from context"
                    % external_subnet_id
                )
                self.net_wrapper.delete_network(external_net)
                LOG.debug(
                    "External network with id '%s' deleted from context"
                    % external_net_id
                )
            except Exception as e:
                msg = "Can't delete external network {} from context: {}".format(
                    external_net_id, e
                )
                LOG.warning(msg)

            cmd = ["sudo", "ip", "link", "delete", "{}.{}".format(self.interface_name, i + 1)]
            proc = subprocess.Popen(cmd)
            proc.wait()
            if proc.returncode == 0:
                LOG.debug("Deleting vlan {}.{} was successful".format(
                          self.interface_name, i + 1))
            else:
                LOG.exception("Deleting vlan {}.{} failed".format(
                              self.interface_name, i + 1))

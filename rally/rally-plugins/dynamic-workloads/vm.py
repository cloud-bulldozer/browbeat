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
import random

import nova_custom
import neutron_custom

LOG = logging.getLogger(__name__)


class VMDynamicScenario(nova_custom.NovaDynamicScenario,
                        neutron_custom.NeutronDynamicScenario):

    def create_delete_servers(self, image, flavor, num_vms=1, min_sleep=0, max_sleep=10,
                              network_create_args=None, subnet_create_args=None):
        """Create <num_vms> servers and delete <num_vms//2> servers.

        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param num_vms: int, number of servers to create
        :param min_sleep: int, minimum duration to sleep before deleting a server
        :param max_sleep: int, maximum duration to sleep before deleting a server
        :param network_create_args: dict, arguments for network creation
        :param subnet_create_args: dict, arguments for subnet creation
        """
        network = self._create_network(network_create_args or {})
        self._create_subnet(network, subnet_create_args or {})
        kwargs = {}
        kwargs["nics"] = [{"net-id": network["network"]["id"]}]
        servers = []
        for i in range(num_vms):
            server = self._boot_server_with_tag(image, flavor, "create_delete", **kwargs)
            LOG.info("Created server {} when i = {}".format(server,i))
            servers.append(server)
            # Delete least recently created server from list when i=1,3,5,7.....
            if i % 2 == 1:
                self.sleep_between(min_sleep, max_sleep)
                server_to_delete = servers[0]
                self._delete_server(server_to_delete, force=True)
                LOG.info("Deleted server {} when i = {}".format(server_to_delete,i))
                servers.pop(0)

    def boot_servers_with_fip(self, image, flavor, ext_net_id, num_vms=1, router_create_args=None,
                              network_create_args=None, subnet_create_args=None, **kwargs):
        """Create <num_vms> servers with floating IPs

        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param ext_net_id: external network ID for floating IP creation
        :param num_vms: int, number of servers to create
        :param router_create_args: dict, arguments for router creation
        :param network_create_args: dict, arguments for network creation
        :param subnet_create_args: dict, arguments for subnet creation
        :param kwargs: dict, Keyword arguments to function
        """
        ext_net_name = None
        if ext_net_id:
            ext_net_name = self.clients("neutron").show_network(ext_net_id)["network"][
                "name"
            ]
        router_create_args["name"] = self.generate_random_name()
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault(
            "external_gateway_info", {"network_id": ext_net_id, "enable_snat": True}
        )
        router = self._create_router(router_create_args)

        network = self._create_network(network_create_args or {})
        subnet = self._create_subnet(network, subnet_create_args or {})
        self._add_interface_router(subnet["subnet"], router["router"])
        for i in range(num_vms):
            kwargs["nics"] = [{"net-id": network["network"]["id"]}]
            guest = self._boot_server_with_fip_and_tag(
                image, flavor, "migrate",
                True, ext_net_name, **kwargs
            )
            self._wait_for_ping(guest[1]["ip"])

    def get_servers_migration_list(self, num_migrate_vms):
        """Generate list of servers to migrate between computes

        :param num_migrate_vms: int, number of servers to migrate between computes
        :returns: list of server objects to migrate between computes
        """
        eligible_servers = self._get_servers_by_tag("migrate")

        random.shuffle(eligible_servers)
        num_servers_to_migrate = min(num_migrate_vms, len(eligible_servers))
        list_of_servers_to_migrate = []

        for i in range(num_servers_to_migrate):
            list_of_servers_to_migrate.append(eligible_servers[i])

        return list_of_servers_to_migrate

    def migrate_servers_with_fip(self, num_migrate_vms):
        """Migrate servers between computes

        :param num_migrate_vms: int, number of servers to migrate between computes
        """
        for server in self.get_servers_migration_list(num_migrate_vms):
            fip = list(server.addresses.values())[0][1]['addr']
            LOG.info("ping {} before server migration".format(fip))
            self._wait_for_ping(fip)
            self._migrate(server)
            self._resize_confirm(server, status="ACTIVE")
            LOG.info("ping {} after server migration".format(fip))
            self._wait_for_ping(fip)

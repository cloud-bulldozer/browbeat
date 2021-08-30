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

import random

import dynamic_utils


class VMDynamicScenario(dynamic_utils.NovaUtils,
                        dynamic_utils.NeutronUtils,
                        dynamic_utils.LockUtils):

    def boot_servers(self, image, flavor, num_vms=2,
                     network_create_args=None, subnet_create_args=None):
        """Create <num_vms> servers.

        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param num_vms: int, number of servers to create
        :param network_create_args: dict, arguments for network creation
        :param subnet_create_args: dict, arguments for subnet creation
        """
        network = self._create_network(network_create_args or {})
        self._create_subnet(network, subnet_create_args or {})
        kwargs = {}
        kwargs["nics"] = [{"net-id": network["network"]["id"]}]
        for _ in range(num_vms):
            server = self._boot_server_with_tag(image, flavor, "create_delete", **kwargs)
            self.log_info("Created server {}".format(server))

    def delete_random_servers(self, num_vms):
        """Delete <num_vms> randomly chosen servers

        :param num_vms: int, number of servers to delete
        """
        eligible_servers = self._get_servers_by_tag("create_delete")
        num_vms = min(num_vms, len(eligible_servers))

        servers_to_delete = random.sample(eligible_servers, num_vms)
        num_servers_deleted = 0
        for server in servers_to_delete:
            server_id = server.id
            if not self.acquire_lock(server_id):
                continue
            # Check that the server has not been
            # deleted already in another iteration.
            try:
                self.show_server(server)
            except Exception as e:
                self.log_info("Server deletion failed as {}".format(e.message))
                self.release_lock(server_id)
                continue
            self.log_info("Deleting server {}".format(server))
            self._delete_server(server, force=True)
            num_servers_deleted += 1
            self.release_lock(server_id)

        if num_servers_deleted == 0:
            self.log_info("""No servers which are not under lock,
                          so cannot perform deletion on any server""")

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
        keypair = self.context["user"]["keypair"]

        for _ in range(num_vms):
            kwargs["nics"] = [{"net-id": network["network"]["id"]}]
            guest = self._boot_server_with_fip_and_tag(
                image, flavor, "migrate_or_swap",
                True, ext_net_name, key_name=keypair["name"], **kwargs
            )
            self._wait_for_ping(guest[1]["ip"])

    def get_servers_migration_list(self, num_migrate_vms):
        """Generate list of servers to migrate between computes

        :param num_migrate_vms: int, number of servers to migrate between computes
        :returns: list of server objects to migrate between computes
        """
        eligible_servers = list(filter(lambda server: self._get_fip_by_server(server) is not False,
                                       self._get_servers_by_tag("migrate_or_swap")))

        num_servers_to_migrate = min(2*num_migrate_vms, len(eligible_servers))
        list_of_servers_to_migrate = random.sample(eligible_servers, num_servers_to_migrate)

        return list_of_servers_to_migrate

    def migrate_servers_with_fip(self, num_migrate_vms):
        """Migrate servers between computes

        :param num_migrate_vms: int, number of servers to migrate between computes
        """
        server_migration_list = self.get_servers_migration_list(num_migrate_vms)

        loop_counter = 0
        num_migrated = 0
        length_server_migration_list = len(server_migration_list)

        while loop_counter < length_server_migration_list and num_migrated < num_migrate_vms:
            server_to_migrate = server_migration_list[loop_counter]

            loop_counter += 1
            if not self.acquire_lock(server_to_migrate.id):
                continue

            fip = self._get_fip_by_server(server_to_migrate)
            self.log_info("ping {} before server migration".format(fip))
            self._wait_for_ping(fip)
            self._migrate(server_to_migrate)
            self._resize_confirm(server_to_migrate, status="ACTIVE")
            self.log_info("ping {} after server migration".format(fip))
            self._wait_for_ping(fip)
            self.release_lock(server_to_migrate.id)
            num_migrated += 1

        if num_migrated == 0:
            self.log_info("""No servers which are not under lock, so
                      cannot migrate any servers.""")

    def swap_floating_ips_between_servers(self):
        """Swap floating IPs between servers
        """
        eligible_servers = list(filter(lambda server: self._get_fip_by_server(server) is not False,
                                       self._get_servers_by_tag("migrate_or_swap")))

        servers_for_swapping = []
        for server in eligible_servers:
            if not self.acquire_lock(server.id):
                continue
            servers_for_swapping.append(server)
            if len(servers_for_swapping) == 2:
                break

        if len(servers_for_swapping) < 2:
            self.log_info("""Number of unlocked servers not sufficient
                          for swapping floating IPs between servers""")
            return

        kwargs = {"floating_ip_address": self._get_fip_by_server(servers_for_swapping[0])}
        server1_fip = self._list_floating_ips(**kwargs)["floatingips"][0]

        kwargs = {"floating_ip_address": self._get_fip_by_server(servers_for_swapping[1])}
        server2_fip = self._list_floating_ips(**kwargs)["floatingips"][0]

        server1_port = server1_fip["port_id"]
        server2_port = server2_fip["port_id"]

        fip_update_dict = {"port_id": None}
        self.clients("neutron").update_floatingip(
            server1_fip["id"], {"floatingip": fip_update_dict})
        self.clients("neutron").update_floatingip(
            server2_fip["id"], {"floatingip": fip_update_dict})

        self.log_info("""Ping until failure after dissociating servers' floating IPs,
                      before swapping""")
        self.log_info("Ping server 1 {} until failure".format(server1_fip["floating_ip_address"]))
        self._wait_for_ping_failure(server1_fip["floating_ip_address"])
        self.log_info("Ping server 2 {} until failure".format(server2_fip["floating_ip_address"]))
        self._wait_for_ping_failure(server2_fip["floating_ip_address"])

        # Swap floating IPs between server1 and server2
        fip_update_dict = {"port_id": server2_port}
        self.clients("neutron").update_floatingip(
            server1_fip["id"], {"floatingip": fip_update_dict}
        )
        fip_update_dict = {"port_id": server1_port}
        self.clients("neutron").update_floatingip(
            server2_fip["id"], {"floatingip": fip_update_dict}
        )

        self.log_info("Ping until success by swapping servers' floating IPs")
        self.log_info("Ping server 1 {} until success".format(server1_fip["floating_ip_address"]))
        self._wait_for_ping(server1_fip["floating_ip_address"])
        self.log_info("Ping server 2 {} until success".format(server2_fip["floating_ip_address"]))
        self._wait_for_ping(server2_fip["floating_ip_address"])

        # Release locks from servers
        self.release_lock(servers_for_swapping[0].id)
        self.release_lock(servers_for_swapping[1].id)

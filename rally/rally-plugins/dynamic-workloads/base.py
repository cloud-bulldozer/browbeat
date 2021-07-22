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
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally_openstack.scenarios.vm import utils as vm_utils

LOG = logging.getLogger(__name__)


class DynamicBase(vm_utils.VMScenario, neutron_utils.NeutronScenario):
    def create_delete_servers(self, image, flavor, num_vms=1, min_sleep=0, max_sleep=10,
                              network_create_args=None, subnet_create_args=None):
        """Creates <num_vms> servers and deletes <num_vms//2> servers.

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
            server = self._boot_server(image, flavor, **kwargs)
            LOG.info("Created server {} when i = {}".format(server,i))
            servers.append(server)
            # Delete least recently created server from list when i=1,3,5,7.....
            if i % 2 == 1:
                self.sleep_between(min_sleep, max_sleep)
                server_to_delete = servers[0]
                self._delete_server(server_to_delete, force=True)
                LOG.info("Deleted server {} when i = {}".format(server_to_delete,i))
                servers.pop(0)

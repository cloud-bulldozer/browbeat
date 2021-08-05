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
import io
from rally.common import sshutils

from rally_openstack.scenarios.octavia import utils as octavia_utils
from octaviaclient.api import exceptions

LOG = logging.getLogger(__name__)


class DynamicOctaviaBase(octavia_utils.OctaviaBase):

    def create_clients(self, num_clients, user, user_data_file, image, flavor, **kwargs):
        """Create <num_clients> clients

        :param num_clients: int, number of clients to create
        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param user: user to ssh
        :param user_data_file: user data file to serve from the metadata server
        :param kwargs: dict, Keyword arguments to function
        """

        _clients = []
        for i in range(num_clients):
            try:
                userdata = io.open(user_data_file, "r")
                kwargs["userdata"] = userdata
                LOG.info("Added user data")
            except Exception as e:
                LOG.info("couldn't add user data %s", e)

            LOG.info("Launching Client : {}".format(i))
            server = self._boot_server(
                image,
                flavor,
                key_name=self.context["user"]["keypair"]["name"],
                **kwargs)
            if hasattr(userdata, 'close'):
                userdata.close()

            for net in server.addresses:
                network_name = net
                break
            if network_name is None:
                return False
            # IP Address
            _clients.append(
                str(server.addresses[network_name][0]["addr"]))
        LOG.info(_clients)
        return _clients

    def create_listener(self, lb_id, protocol_port, max_attempts=10):
        """Create a listener.
        :param lb_id: ID of loadbalancer
        :param protocol_port: protocol port number for the listener
        :param max_attempts: max retries
        """

        listener_args = {
            "name": self.generate_random_name(),
            "loadbalancer_id": lb_id,
            "protocol": 'HTTP',
            "protocol_port": protocol_port,
            "connection_limit": -1,
            "admin_state_up": True,
        }
        LOG.info("Creating a listener for lb {}".format(lb_id))
        attempts = 0
        # Retry to avoid HTTP 409 errors like "Load Balancer
        # is immutable and cannot be updated"
        while attempts < max_attempts:
            try:
                listener = self.octavia.listener_create(json={"listener": listener_args})
                break
            except exceptions.OctaviaClientException as e:
                # retry for 409 return code
                if e.code == 409:
                    attempts += 1
                    time.sleep(60)
                    continue
                break
        LOG.info("Listener created {}".format(listener))
        LOG.info("Waiting for the lb {} to be active, after listener_create"
                 .format(lb_id))
        return listener

    def create_pool(self, lb_id, listener_id, max_attempts=10):
        """Create a pool.
        :param lb_id: ID of loadbalancer
        :param listener_id: ID of listener
        :param max_attempts: max retries
        """

        LOG.info("Creating a pool for lb {}".format(lb_id))
        attempts = 0
        # Retry to avoid HTTP 409 errors like "Load Balancer
        # is immutable and cannot be updated"
        while attempts < max_attempts:
            try:
                # internally pool_create will wait for active state
                pool = self.octavia.pool_create(
                    lb_id=lb_id,
                    protocol='HTTP',
                    lb_algorithm='ROUND_ROBIN',
                    listener_id=listener_id,
                    admin_state_up=True)
                break
            except exceptions.OctaviaClientException as e:
                # retry for 409 return code
                if e.code == 409:
                    attempts += 1
                    time.sleep(120)
                    continue
                break
        return pool

    def create_member(self, client_ip, pool_id, protocol_port, subnet_id, lb_id, max_attempts=10):
        """Create a member.
        :param client_ip: client ip address
        :param pool_id: ID of pool
        :param subnet_id: subnet ID for pool
        :param lb_id: ID of loadbalancer
        :param max_attempts: max retries
        """

        member_args = {
            "address": client_ip,
            "protocol_port": protocol_port,
            "subnet_id": subnet_id,
            "admin_state_up": True,
            "name": self.generate_random_name(),
        }
        LOG.info("Adding member : {} to the pool {} lb {}"
                 .format(client_ip, pool_id, lb_id))
        attempts = 0
        # Retry to avoid "Load Balancer is immutable and cannot be updated"
        while attempts < max_attempts:
            try:
                self.octavia.member_create(pool_id,
                                           json={"member": member_args})
                break
            except exceptions.OctaviaClientException as e:
                # retry for 409 return code
                if e.code == 409:
                    attempts += 1
                    time.sleep(120)
                    LOG.info("mem_create exception: Waiting for the lb {} to be active"
                             .format(lb_id))
                    continue
                break
        time.sleep(30)
        LOG.info("Waiting for the lb {} to be active, after member_create"
                 .format(lb_id))

    def check_connection(self, lb, user, jump_host_ip, num_pools, num_clients, max_attempts=10):
        """Checks the connection
        :param lb: loadbalancer
        :param user: ssh user
        :param jump_host_ip: Floating IP of jumphost
        :param num_pools: number of pools per loadbalancer
        :param num_clients: number of clients per loadbalancer
        :param max_attempts: max retries
        """

        port = 80
        lb_ip = lb["vip_address"]
        LOG.info("Load balancer IP: {}".format(lb_ip))
        jump_ssh = sshutils.SSH(user, jump_host_ip, 22, None, None)
        # check for connectivity
        self._wait_for_ssh(jump_ssh)
        for i in range(num_pools):
            for j in range(num_clients):
                cmd = "curl -s {}:{}".format(lb_ip, port)
                attempts = 0
                while attempts < max_attempts:
                    test_exitcode, stdout_test, stderr = jump_ssh.execute(cmd, timeout=60)
                    LOG.info("cmd: {}, stdout:{}".format(cmd, stdout_test))
                    if stdout_test != '1':
                        LOG.error("ERROR with HTTP response {}".format(cmd))
                        attempts += 1
                        time.sleep(30)
                    else:
                        LOG.info("cmd: {} successful".format(cmd))
                        break
            port = port + 1

    def create_loadbalancers(
        self, octavia_image, octavia_flavor, user, num_lbs, jump_host_ip, vip_subnet_id,
        user_data_file, num_pools, num_clients, router_create_args=None,
        network_create_args=None, subnet_create_args=None, **kwargs):

        """Create <num_lbs> loadbalancers with specified <num_pools> <num_clients> per Loadbalancer.

        :param octavia_image: image ID or instance for server creation
        :param octavia_flavor: int, flavor ID or instance for server creation
        :param user: ssh user
        :param num_lbs: int, number of loadbalancers to create
        :param jump_host_ip: floating ip of jumphost
        :param vip_subnet_id: Set subnet for the load balancer (name or ID)
        :param user_data_file: pass user-data file for clients
        :param num_pools: int, number of pools to create
        :param num_clients: int, number of clients to create
        :param router_create_args: dict, arguments for router creation
        :param network_create_args: dict, arguments for network creation
        :param subnet_create_args: dict, arguments for subnet creation
        :param kwargs: dict, Keyword arguments to function
        """

        network = self._create_network(network_create_args or {})
        subnet = self._create_subnet(network, subnet_create_args or {})
        kwargs["nics"] = [{"net-id": network['network']['id']}]
        subnet_id = subnet['subnet']['id']
        _clients = self.create_clients(num_clients, user, user_data_file, octavia_image,
                                       octavia_flavor, **kwargs)
        LOG.info("Creating a load balancer")
        for _ in range(num_lbs):
            protocol_port = 80
            lb = self.octavia.load_balancer_create(subnet_id=vip_subnet_id, admin_state=True)
            lb_id = lb["id"]
            LOG.info("Waiting for the lb {} to be active".format(lb["id"]))
            self.octavia.wait_for_loadbalancer_prov_status(lb)
            time.sleep(90)
            for _ in range(num_pools):
                listener = self.create_listener(lb_id, protocol_port)
                self.octavia.wait_for_loadbalancer_prov_status(lb)
                pool = self.create_pool(lb_id, listener["listener"]["id"])
                self.octavia.wait_for_loadbalancer_prov_status(lb)
                for client_ip in _clients:
                    self.create_member(client_ip, pool["id"], protocol_port, subnet_id, lb_id)
                protocol_port = protocol_port + 1
            self.check_connection(lb, user, jump_host_ip, num_pools, num_clients)

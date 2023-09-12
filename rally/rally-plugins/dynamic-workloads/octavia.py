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

import io
import time
import random
from rally.utils import sshutils

from rally_openstack.task.scenarios.octavia import utils as octavia_utils
from octaviaclient.api import exceptions
import dynamic_utils


class DynamicOctaviaBase(octavia_utils.OctaviaBase, dynamic_utils.NovaUtils):
    def build_jump_host(self, ext_net_name, image, flavor, user, subnet, password=None, **kwargs):
        """Builds jump host

        :param ext_net_name: External network name
        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param user: user to ssh
        :param subnet: subnet
        :param kwargs: dict, Keyword arguments to function
        """

        kwargs["nics"] = [{"net-id": subnet['network_id']}]
        keyname = self.context["user"]["keypair"]["name"]
        self.log_info("Building Jump Host with key : {}".format(keyname))
        jump_host, jump_host_ip = self._boot_server_with_fip(image,
                                                             flavor,
                                                             True,
                                                             floating_network=ext_net_name,
                                                             key_name=keyname,
                                                             **kwargs)
        # wait for ping
        self._wait_for_ping(jump_host_ip["ip"])

        # open ssh connection
        jump_ssh = sshutils.SSH(user, jump_host_ip["ip"], 22, self.context[
                                "user"]["keypair"]["private"], password)

        # check for connectivity
        self._wait_for_ssh(jump_ssh)

        # write id_rsa(private key) to get to guests
        self._run_command_over_ssh(jump_ssh, {"remote_path": "rm -rf ~/.ssh"})
        self._run_command_over_ssh(jump_ssh, {"remote_path": "mkdir ~/.ssh"})
        jump_ssh.run(
            "cat > ~/.ssh/id_rsa",
            stdin=self.context["user"]["keypair"]["private"])
        jump_ssh.execute("chmod 0600 ~/.ssh/id_rsa")
        return jump_ssh, jump_host_ip, jump_host

    def create_clients_lb(self, num_clients, user, user_data_file, image,
                          flavor, subnet, lb_subnet, **kwargs):
        """Create <num_clients> clients

        :param num_clients: int, number of clients to create
        :param user: user to ssh
        :param user_data_file: user data file to serve from the metadata server
        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param subnet: subnet
        :param lb_subnet: subnet of loadbalancer
        :param kwargs: dict, Keyword arguments to function
        """

        kwargs["nics"] = [{"net-id": subnet['network_id']}]
        _clients = []
        for i in range(num_clients):
            try:
                userdata = io.open(user_data_file, "r")
                kwargs["userdata"] = userdata
                self.log_info("Added user data")
            except Exception as e:
                self.log_info("couldn't add user data %s" % e)

            self.log_info("Launching Client : {}".format(i))
            tag = "client:"+str(lb_subnet['network_id'])
            kwargs['description'] = subnet['network_id']
            # server description consists of network_id
            server = self._boot_server_with_tag(image, flavor, tag, **kwargs)
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
        self.log_info(_clients)
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
        self.log_info("Creating a listener for lb {}".format(lb_id))
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
        self.log_info("Listener created {}".format(listener))
        self.log_info("Waiting for the lb {} to be active, after listener_create".format(
            lb_id))
        return listener

    def create_pool(self, lb_id, listener_id, max_attempts=10):
        """Create a pool.
        :param lb_id: ID of loadbalancer
        :param listener_id: ID of listener
        :param max_attempts: max retries
        """

        self.log_info("Creating a pool for lb {}".format(lb_id))
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
        self.log_info("Adding member : {} to the pool {} lb {}".format(
            client_ip, pool_id, lb_id))
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
                    msg = "mem_create exception: Waiting for the lb {} to be active".format(lb_id)
                    self.log_info(msg)
                    continue
                break
        time.sleep(30)
        self.log_info("Waiting for the lb {} to be active, after member_create".format(
            lb_id))

    def check_connection(self, lb, jump_ssh, num_pools, num_clients, max_attempts=10):
        """Checks the connection
        :param lb: loadbalancer
        :param jump_host_ip: Floating IP of jumphost
        :param num_pools: number of pools per loadbalancer
        :param num_clients: number of clients per loadbalancer
        :param max_attempts: max retries
        """

        port = 80
        lb_ip = lb["vip_address"]
        self.log_info("Load balancer IP: {}".format(lb_ip))
        # check for connectivity
        self._wait_for_ssh(jump_ssh)
        for i in range(num_pools):
            for j in range(num_clients):
                cmd = "curl -s {}:{}".format(lb_ip, port)
                attempts = 0
                while attempts < max_attempts:
                    test_exitcode, stdout_test, stderr = jump_ssh.execute(cmd, timeout=60)
                    self.log_info("cmd: {}, stdout:{}".format(cmd, stdout_test))
                    if stdout_test != '1':
                        self.log_error("ERROR with HTTP response {}".format(cmd))
                        attempts += 1
                        time.sleep(30)
                    else:
                        self.log_info("cmd: {} successful".format(cmd))
                        break
                if attempts == max_attempts:
                    raise Exception("Connection check failed for pool {} and client {} on lb {}.".
                                    format(i, j, lb_ip))
            port = port + 1

    def create_loadbalancers(
        self, octavia_image, octavia_flavor, user, num_lbs, user_data_file,
        num_pools, num_clients, ext_net_id, router_create_args=None,
        network_create_args=None, subnet_create_args=None,
        **kwargs):

        """Create <num_lbs> loadbalancers with specified <num_pools> <num_clients> per Loadbalancer.

        :param octavia_image: image ID or instance for server creation
        :param octavia_flavor: int, flavor ID or instance for server creation
        :param user: ssh user
        :param num_lbs: int, number of loadbalancers to create
        :param user_data_file: pass user-data file for clients
        :param num_pools: int, number of pools to create
        :param num_clients: int, number of clients to create
        :param ext_net_id: external network ID
        :param router_create_args: dict, arguments for router creation
        :param network_create_args: dict, arguments for network creation
        :param subnet_create_args: dict, arguments for subnet creation
        :param kwargs: dict, Keyword arguments to function
        """

        if ext_net_id:
            ext_net_name = self.clients("neutron").show_network(
                ext_net_id)["network"]["name"]
        router_create_args["name"] = self.generate_random_name()
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault("external_gateway_info",
                                      {"network_id": ext_net_id, "enable_snat": True})
        router = self._create_router(router_create_args)
        for _ in range(num_lbs):
            subnets = []
            num_networks = 2
            for net in range(0, num_networks):
                network = self._create_network(network_create_args or {})
                subnet = self._create_subnet(network, subnet_create_args or {})
                subnets.append(subnet)
            self._add_interface_router(subnets[0]['subnet'], router['router'])
            self.log_info("Subnets {}".format(subnets))
            vip_subnet_id = subnets[0]['subnet']['id']
            mem_subnet_id = subnets[1]['subnet']['id']

            # network1 is used by jumphost and LB
            # network2 is used by clients (members)
            jump_ssh, jump_host_ip, jump_host = self.build_jump_host(
                ext_net_name, octavia_image, octavia_flavor, user, subnets[0]['subnet'], **kwargs)

            _clients = self.create_clients_lb(num_clients, user, user_data_file, octavia_image,
                                              octavia_flavor, subnets[1]['subnet'],
                                              subnets[0]['subnet'], **kwargs)

            protocol_port = 80
            # description consists of router id
            lb = self.octavia.load_balancer_create(subnet_id=vip_subnet_id,
                                                   description=router['router']['id'],
                                                   admin_state=True)
            lb_id = lb["id"]
            self.log_info("Waiting for the lb {} to be active".format(lb["id"]))
            self.octavia.wait_for_loadbalancer_prov_status(lb)
            time.sleep(90)

            for _ in range(num_pools):
                listener = self.create_listener(lb_id, protocol_port)
                self.octavia.wait_for_loadbalancer_prov_status(lb)
                pool = self.create_pool(lb_id, listener["listener"]["id"])
                self.octavia.wait_for_loadbalancer_prov_status(lb)
                for client_ip in _clients:
                    self.create_member(client_ip, pool["id"], protocol_port, mem_subnet_id, lb_id)
                protocol_port = protocol_port + 1
            self.check_connection(lb, jump_ssh, num_pools, num_clients)
            self._delete_server_with_fip(jump_host, jump_host_ip)
            self.log_info("Deleted Jump_host {}".format(jump_host_ip))

    def delete_loadbalancers(self, delete_num_lbs):
        """Deletes <delete_num_lbs> loadbalancers randomly
        with associated resources

        :param delete_num_lbs: number of loadbalancers to delete
        """

        lb_list = self.octavia.load_balancer_list()
        for _ in range(delete_num_lbs):
            random_lb = random.choice(lb_list["loadbalancers"])
            # delete the lb
            self.octavia._clients.octavia().load_balancer_delete(random_lb["id"], cascade=True)
            self.log_info("Random LB deleted {}".format(random_lb["id"]))
            time.sleep(15)
            # delete vm's that were added as members to lb
            tag = "client:"+str(random_lb['vip_network_id'])
            servers = self._get_servers_by_tag(tag)
            for server in servers:
                self._delete_server(server)
            subnet_id = {'id': random_lb['vip_subnet_id']}
            # fetch router id from the description of lb
            router_id = {'id': random_lb['description']}
            self._remove_interface_router(subnet_id, router_id)
            # delete lb network
            self.admin_clients("neutron").delete_network(random_lb['vip_network_id'])
            lb_list["loadbalancers"].remove(random_lb)
            # get net_id from description and delete client network
            self.admin_clients("neutron").delete_network(servers[0].description)

    def delete_members_random_lb(self, delete_num_members, max_attempts=10):
        """Deletes members from a random loadbalancer
        :param delete_num_members: number of members to delete
        """

        lb_list = self.octavia.load_balancer_list()
        random_lb = random.choice(lb_list["loadbalancers"])
        self.log_info("Random LB selected {}".format(random_lb))
        self.octavia.wait_for_loadbalancer_prov_status(random_lb)
        random_lb_pool = random.choice(random_lb["pools"])
        self.log_info("Random pool {}".format(random_lb_pool))
        members_list = self.octavia.member_list(random_lb_pool['id'])
        for i in range(delete_num_members):
            attempts = 0
            random_member = random.choice(members_list['members'])
            # Retry to avoid "Pool is immutable and cannot be updated"
            while attempts < max_attempts:
                try:
                    self.octavia._clients.octavia().member_delete(random_lb_pool['id'],
                                                                  random_member['id'])
                    self.log_info("Member-{} deleted {}".format(i, random_member['id']))
                    break
                except exceptions.OctaviaClientException as e:
                    # retry for 409 return code
                    if e.code == 409:
                        attempts += 1
                        time.sleep(30)
                        continue
                    break

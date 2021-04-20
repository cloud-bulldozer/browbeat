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
from rally.common import sshutils
from rally_openstack import consts
from rally_openstack.scenarios.vm import utils as vm_utils
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally_openstack.scenarios.octavia import utils as octavia_utils
from rally.task import scenario
from rally.task import types
from rally.task import validation


LOG = logging.getLogger(__name__)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services", services=[consts.Service.NEUTRON,
                                               consts.Service.NOVA,
                                               consts.Service.OCTAVIA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["octavia", "neutron", "nova"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.abench", platform="openstack")
class BrowbeatApacheBench(vm_utils.VMScenario,
                          neutron_utils.NeutronScenario,
                          octavia_utils.OctaviaBase):
    def build_jump_host(self, external, image, flavor, user, password=None, **kwargs):
        keyname = self.context["user"]["keypair"]["name"]
        LOG.info("Building Jump Host with key : {}".format(keyname))
        jump_host, jump_host_ip = self._boot_server_with_fip(image,
                                                             flavor,
                                                             True,
                                                             None,
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

    def create_clients(self, jump_ssh, num_clients, image, flavor, user, **kwargs):
        _clients = []
        for i in range(num_clients):
            LOG.info("Launching Client : {}".format(i))
            server = self._boot_server(
                image,
                flavor,
                key_name=self.context["user"]["keypair"]["name"],
                **kwargs)
            for net in server.addresses:
                network_name = net
                break
            if network_name is None:
                return False
            # IP Address
            _clients.append(
                str(server.addresses[network_name][0]["addr"]))
        return _clients

    def run(self, image, flavor, user, subnet_id, lb_algorithm, protocol, protocol_port,
            total_requests, concurrency_level, description=None, admin_state=None,
            listeners=None, flavor_id=None, provider=None, external=None,
            vip_qos_policy_id=None, send_results=True, num_clients=2, password="",
            network_id=None, **kwargs):

            kwargs["nics"] = [{"net-id": network_id}]
            jump_ssh, jump_host_ip, jump_host = self.build_jump_host(
                external, image, flavor, user, **kwargs)
            _clients = self.create_clients(
                jump_ssh, num_clients, image, flavor, user, **kwargs)

            LOG.info("Creating a load balancer")
            # create a loadbalancer, listener, pool and add members to the pool
            lb = self.octavia.load_balancer_create(
                subnet_id=subnet_id,
                admin_state=True)
            LOG.info("Waiting for the load balancer to be active")
            self.octavia.wait_for_loadbalancer_prov_status(lb)
            time.sleep(90)
            lb_id = lb_id = lb["id"]
            listener_args = {
                "name": self.generate_random_name(),
                "loadbalancer_id": lb_id,
                "protocol": protocol,
                "protocol_port": protocol_port,
                "connection_limit": -1,
                "admin_state_up": True,
                "default_tls_container_ref": None,
                "description": None,
                "insert_headers": None,
                "l7policies": [],
                "sni_container_refs": [],
                "timeout_client_data": 50000,
                "timeout_member_connect": 5000,
                "timeout_member_data": 50000,
                "timeout_tcp_inspect": 0,
            }
            LOG.info("Creating a listener")
            listener = self.octavia.listener_create(
                json={"listener": listener_args})
            time.sleep(30)
            LOG.info("Creating a pool")
            pool = self.octavia.pool_create(
                lb_id=lb["id"],
                protocol=protocol,
                lb_algorithm=lb_algorithm,
                listener_id=listener["listener"]["id"],
                admin_state_up=True)
            # member_create(pool_id, args), subnet_id, address, protocol_port, pool_id
            time.sleep(60)
            for client_ip in _clients:
                member_args = {
                    "address": client_ip,
                    "protocol_port": protocol_port,
                    "subnet_id": subnet_id,
                    "admin_state_up": True,
                    "weight": 1,
                    "monitor_port": None,
                    "monitor_address": None,
                    "name": self.generate_random_name(),
                    "backup": False,
                }
                LOG.info("Adding member : {} to the pool".format(client_ip))
                self.octavia.member_create(
                    pool["id"],
                    json={"member": member_args})
                time.sleep(30)
            # execute command, stdout will have infomation
            time.sleep(90)
            lb_ip = lb["vip_address"]
            lb_ip += "/"
            LOG.info("Load balancer IP: {}".format(lb_ip))
            cmd = "ab -n {} -c {} {}".format(total_requests, concurrency_level, lb_ip)
            LOG.info("Running command : {}".format(cmd))
            ab_exitcode, stdout_ab, stderr = jump_ssh.execute(cmd, timeout=0)
            # prepare results
            report = []
            self.add_output(
                additive={"title": "ApacheBench Stats",
                          "description": "ApacheBench Scenario",
                          "chart_plugin": "StatsTable",
                          "label": "Gbps",
                          "data": report})

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
from rally_openstack import consts
from rally_openstack.scenarios.vm import utils as vm_utils
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally_openstack.scenarios.octavia import utils as octavia_utils
from octaviaclient.api import exceptions

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
@validation.add("required_contexts", contexts=["network"])
@scenario.configure(context={"cleanup@openstack": ["octavia", "neutron", "nova"],
                    "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.OctaviaCreateLoadbalancerListenersPoolsMembers",
                    platform="openstack")
class OctaviaCreateLoadbalancerListenersPoolsMembers(vm_utils.VMScenario,
                                                     neutron_utils.NeutronScenario,
                                                     octavia_utils.OctaviaBase):

    def create_clients(self, num_clients, image, flavor, user, user_data_file, **kwargs):
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

    def run(self, image, flavor, user, lb_algorithm, protocol, protocol_port,
            jump_host_ip, num_pools, num_clients, vip_subnet_id, user_data_file,
            router_create_args=None, network_create_args=None,
            subnet_create_args=None, **kwargs):

        network = self._create_network(network_create_args or {})
        subnet = self._create_subnet(network, subnet_create_args or {})
        kwargs["nics"] = [{"net-id": network['network']['id']}]
        subnet_id = subnet['subnet']['id']
        _clients = self.create_clients(num_clients, image,
                                       flavor, user, user_data_file,
                                       **kwargs)
        max_attempts = 10
        LOG.info("Creating a load balancer")
        lb = self.octavia.load_balancer_create(
            subnet_id=vip_subnet_id,
            admin_state=True)
        LOG.info("Waiting for the load balancer to be active")
        self.octavia.wait_for_loadbalancer_prov_status(lb)
        time.sleep(90)
        lb_id = lb["id"]

        for _ in range(num_pools):
            listener_args = {
                "name": self.generate_random_name(),
                "loadbalancer_id": lb_id,
                "protocol": protocol,
                "protocol_port": protocol_port,
                "connection_limit": -1,
                "admin_state_up": True,
            }
            LOG.info("Creating a listener")
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
                        attempts += attempts
                        time.sleep(120)
                        self.octavia.wait_for_loadbalancer_prov_status(lb)
                        continue
                    break
            LOG.info(listener)
            time.sleep(30)
            self.octavia.wait_for_loadbalancer_prov_status(lb)

            LOG.info("Creating a pool")
            attempts = 0
            # Retry to avoid HTTP 409 errors like "Load Balancer
            # is immutable and cannot be updated"
            while attempts < max_attempts:
                try:
                    # internally pool_create will wait for active state
                    pool = self.octavia.pool_create(
                        lb_id=lb["id"],
                        protocol=protocol,
                        lb_algorithm=lb_algorithm,
                        listener_id=listener["listener"]["id"],
                        admin_state_up=True)
                    break
                except exceptions.OctaviaClientException as e:
                    # retry for 409 return code
                    if e.code == 409:
                        attempts += attempts
                        time.sleep(120)
                        continue
                    break

            time.sleep(60)
            for client_ip in _clients:
                member_args = {
                    "address": client_ip,
                    "protocol_port": protocol_port,
                    "subnet_id": subnet_id,
                    "admin_state_up": True,
                    "name": self.generate_random_name(),
                }
                LOG.info("Adding member : {} to the pool".format(client_ip))
                attempts = 0
                # Retry to avoid "Load Balancer is immutable and cannot be updated"
                while attempts < max_attempts:
                    try:
                        self.octavia.member_create(pool["id"],
                                                   json={"member": member_args})
                        break
                    except exceptions.OctaviaClientException as e:
                        # retry for 409 return code
                        if e.code == 409:
                            attempts += attempts
                            time.sleep(120)
                            self.octavia.wait_for_loadbalancer_prov_status(lb)
                            continue
                        break
                time.sleep(30)
                self.octavia.wait_for_loadbalancer_prov_status(lb)
            protocol_port = protocol_port + 1
        # ssh and ping the vip
        lb_ip = lb["vip_address"]
        LOG.info("Load balancer IP: {}".format(lb_ip))
        port = 80
        for i in range(num_pools):
            jump_ssh = sshutils.SSH(user, jump_host_ip, 22, None, None)
            # check for connectivity
            self._wait_for_ssh(jump_ssh)
            for j in range(num_clients):
                cmd = "curl -s --retry {} {}:{}".format(10, lb_ip, port)
                test_exitcode, stdout_test, stderr = jump_ssh.execute(cmd, timeout=0)
                LOG.info("cmd: {}, stdout:{}".format(cmd, stdout_test))
                if test_exitcode != 0 and stdout_test != 1:
                    LOG.error("ERROR with HTTP response {}".format(cmd))
            port = port + 1

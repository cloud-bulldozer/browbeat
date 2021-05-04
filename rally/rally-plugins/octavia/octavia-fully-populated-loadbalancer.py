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
import logging
import time

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
@validation.add("required_contexts", contexts=["network"])
@scenario.configure(context={"cleanup@openstack": ["octavia", "neutron", "nova"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.OctaviaFullyPopulatedLoadbalancer", platform="openstack")
class OctaviaFullyPopulatedLoadbalancer(vm_utils.VMScenario, neutron_utils.NeutronScenario,
                                        octavia_utils.OctaviaBase):

    def create_client(self, image, flavor, num_lb, project_id, user_data_file):
        addresses = []
        network = self._create_network({'project_id': project_id})
        subnets = self._create_subnets(network, None, None, int(num_lb))
        kwargs = {}
        kwargs["nics"] = []
        for subnet in subnets:
            port_create_args = {}
            port_create_args["fixed_ips"] = [{'subnet_id': subnet["subnet"]["id"]}]
            port_create_args["network_id"] = network["network"]["id"]
            port = self._create_port(network, port_create_args)
            kwargs["nics"].append({'port-id': port['port']['id']})
            addresses.append(port['port']['fixed_ips'][0]['ip_address'])

        LOG.info(addresses)
        userdata = None
        try:
            userdata = io.open(user_data_file, "r")
            kwargs["userdata"] = userdata
        except Exception as e:
            LOG.info("couldn't add user data %s", e)

        self._boot_server(image, flavor, **kwargs)
        if hasattr(userdata, 'close'):
            userdata.close()
        LOG.info(addresses)
        return addresses

    def run(self, image, flavor, vip_subnet_id, num_lb, user_data_file, **kwargs):
        project_id = self.context["tenant"]["id"]

        addresses = self.create_client(image, flavor, num_lb,
                                       project_id, user_data_file)

        loadbalancers = []
        protocol = "HTTP"
        protocol_port = 80
        for mem_addr in addresses:
            lb_name = self.generate_random_name()
            listener_name = self.generate_random_name()
            pool_name = self.generate_random_name()
            LOG.info("Creating load balancer %s", lb_name)
            listener_args = {
                "name": listener_name,
                "protocol": protocol,
                "protocol_port": protocol_port,
                "default_pool": {"name": pool_name},
            }
            pool_args = {
                "name": pool_name,
                "protocol": protocol,
                "lb_algorithm": "ROUND_ROBIN",
                "members": [
                    {
                        "address": mem_addr,
                        "protocol_port": 80
                    }
                ]
            }
            lb_args = {
                "name": lb_name,
                "description": None,
                "listeners": [listener_args],
                "pools": [pool_args],
                "provider": None,
                "admin_state_up": True,
                "project_id": project_id,
                "vip_subnet_id": vip_subnet_id,
                "vip_qos_policy_id": None,
            }

            lb = self.octavia._clients.octavia().load_balancer_create(
                json={"loadbalancer": lb_args})["loadbalancer"]
            loadbalancers.append(lb)

        for loadbalancer in loadbalancers:
            LOG.info("Waiting for the load balancer to be active")
            self.octavia.wait_for_loadbalancer_prov_status(loadbalancer)
            LOG.info("Loadbalancer %s is active", loadbalancer)
            time.sleep(90)

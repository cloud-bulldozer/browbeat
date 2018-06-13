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

from rally_openstack import consts
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally.task import scenario
from rally.task import validation
import subprocess
import time


@validation.add("required_services",services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="BrowbeatPlugin.PortCreateAssociate", platform="openstack")
class PortCreateAssociate(neutron_utils.NeutronScenario):

    def run(self, hypervisor, num_ports=1, user='heat-admin', ssh_config=None, wait=360,
            network_create_args=None, subnet_create_args=None, create_port_args=None, **kwargs):

        neutron = self.admin_clients("neutron")
        ports = []
        neutron.list_agents()

        if create_port_args is None:
            create_port_args = {'binding:host_id': hypervisor}
        else:
            create_port_args['binding:host_id'] = hypervisor

        network = self._create_network(network_create_args or {})
        self._create_subnet(network, subnet_create_args or {})

        for port in range(num_ports):
            create_port_args['network_id'] = network['network']['id']
            port = neutron.create_port({"port": create_port_args})
            ports.append(port)
        server = hypervisor.split('.')[0]

        ssh_cmd = "ssh -F {} {}@{}".format(ssh_config, user, server)
        port_num = 0
        for port in ports:
            cmd = "sudo ovs-vsctl -- --may-exist add-port br-int {}".format(
                "port-{}".format(port_num))
            cmd += " -- set Interface {} type=internal".format(
                "port-{}".format(port_num))
            cmd += " -- set Interface {} external-ids:iface-status=active".format(
                "port-{}".format(port_num))
            cmd += " -- set Interface {} external-ids:attached-mac={}".format(
                "port-{}".format(port_num), port['port']['mac_address'])
            cmd += " -- set Interface {} external-ids:iface-id={}".format(
                "port-{}".format(port_num), port['port']['id'])
            subprocess.call("{} {}".format(ssh_cmd, cmd), shell=True)
            port_num = port_num + 1
            for look in range(30):
                if 'ACTIVE' in neutron.show_port(port["port"]["id"])["port"]["status"]:
                    break
                else:
                    time.sleep(1)

        time.sleep(wait)

        # Cleanup
        if len(ports) > 0 :
            for num in range(len(ports)):
                subprocess.call(
                    "{} sudo ovs-vsctl del-port port-{}".format(ssh_cmd, num), shell=True)

            for port in ports:
                self._delete_port(port)

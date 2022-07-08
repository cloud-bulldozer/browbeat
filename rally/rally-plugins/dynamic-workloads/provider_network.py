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
import os
import subprocess

from rally_openstack.task.scenarios.neutron import utils as neutron_utils
import dynamic_utils
from rally.task import atomic


class DynamicProviderNetworkBase(dynamic_utils.NovaUtils, neutron_utils.NeutronScenario):

    @atomic.action_timer("neutron.create_network")
    def _create_provider_network(self, provider_phys_net):
        """Create neutron provider network.
        :param provider_phys_net: provider physical network
        :returns: neutron network dict
        """
        project_id = self.context["tenant"]["id"]
        body = {
            "name": self.generate_random_name(),
            "tenant_id": project_id,
            "provider:network_type": "vlan",
            "provider:physical_network": provider_phys_net
        }
        # provider network can be created by admin client only
        return self.admin_clients("neutron").create_network({"network": body})

    @atomic.action_timer("neutron.show_network")
    def _show_provider_network(self, provider_network):
        """Fetches information of a certain provider network.
        :param provider_network: provider network object
        """

        return self.admin_clients("neutron").show_network(provider_network['network']['id'])

    @atomic.action_timer("neutron.delete_network")
    def _delete_provider_network(self, provider_network):
        """Delete neutron provider network.
        :param provider_network: provider network object
        """

        return self.admin_clients("neutron").delete_network(provider_network['network']['id'])

    def ping_server(self, server, iface_name, iface_mac, network, subnet):
        """Ping server created on provider network
        :param server: server object
        :param iface_name: interface name
        :param iface_mac: interface MAC
        :param network: provider network object
        :param subnet: subnet object
        """

        internal_network = list(server.networks)[0]
        server_ip = server.addresses[internal_network][0]["addr"]
        server_mac = server.addresses[internal_network][0]["OS-EXT-IPS-MAC:mac_addr"]
        gateway = subnet['subnet']['gateway_ip']
        vlan = network['network']['provider:segmentation_id']
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "scapy_icmp.py")
        cmd = ["sudo", file_path, server_ip, server_mac, gateway, iface_mac, iface_name, str(vlan)]
        proc = subprocess.Popen(cmd)
        proc.wait()
        if proc.returncode == 0:
            self.log_info("Ping to {} is successful".format(server_ip))
        else:
            self.log_info("Ping to {} is failed".format(server_ip))

    def provider_netcreate_nova_boot_ping(self, image, flavor, provider_phys_net, iface_name,
                                          iface_mac, num_vms_provider_net, router_create_args=None,
                                          network_create_args=None,
                                          subnet_create_args=None,
                                          **kwargs):
        """Create provider network, Boot and Ping VM
        :param image: image ID or image name
        :param flavor: flavor ID or flavor name
        :param provider_phys_net: provider physical network
        :param iface_name: interface name
        :param iface_mac: interface MAC
        :param num_vms_provider_net: int, number of vm's to create
        :param router_create_args: dict, arguments for router creation
        :param network_create_args: dict, arguments for network creation
        :param subnet_create_args: dict, arguments for subnet creation
        :param kwargs: dict, Keyword arguments to function
        """

        provider_network = self._create_provider_network(provider_phys_net)
        subnet = self._create_subnet(provider_network, subnet_create_args or {})
        kwargs["nics"] = [{'net-id': provider_network['network']['id']}]
        tag = "provider_network:"+str(provider_network['network']['id'])
        for _ in range(num_vms_provider_net):
            server = self._boot_server_with_tag(image, flavor, tag, **kwargs)
            self.log_info(" Server {} created on provider network {}".format(
                server, provider_network))
            self.ping_server(server, iface_name, iface_mac, provider_network, subnet)

    def pick_random_provider_net(self, provider_phys_net, **kwargs):
        """Picks random provider network that exists
        :param provider_phys_net: provider physical network
        :param kwargs: dict, Keyword arguments to function
        """

        kwargs["provider:physical_network"] = provider_phys_net
        nets = self._list_networks(**kwargs)
        return self._show_provider_network({'network': random.choice(nets)})

    def provider_net_nova_boot_ping(self, provider_phys_net, iface_name,
                                    iface_mac, image, flavor, **kwargs):
        """Boot a VM on a random provider network that exists and Ping
        :param provider_phys_net: provider physical network
        :param iface_name: interface name
        :param iface_mac: interface MAC
        :param image: image ID or image name
        :param flavor: flavor ID or flavor name
        :param kwargs: dict, Keyword arguments to function
        """

        random_network = self.pick_random_provider_net(provider_phys_net)
        kwargs["nics"] = [{'net-id': random_network['network']['id']}]
        tag = "provider_network:"+str(random_network['network']['id'])
        server = self._boot_server_with_tag(image, flavor, tag, **kwargs)
        subnet_id = random_network['network']['subnets'][0]
        subnet = self.admin_clients("neutron").show_subnet(subnet_id)
        self.ping_server(server, iface_name, iface_mac, random_network, subnet)

    def provider_net_nova_delete(self, provider_phys_net, **kwargs):
        """Delete all the VM's on the provider network and then
           the network.
        :param provider_phys_net: provider physical network
        :param kwargs: dict, Keyword arguments to function
        """

        random_network = self.pick_random_provider_net(provider_phys_net)
        kwargs["nics"] = [{'net-id': random_network['network']['id']}]
        tag = "provider_network:"+str(random_network['network']['id'])
        servers = self._get_servers_by_tag(tag)
        for server in servers:
            self._delete_server(server)
        self._delete_provider_network(random_network)

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

from rally_openstack.common import consts
from rally_openstack.task.scenarios.vm import utils as vm_utils
from rally_openstack.task.scenarios.neutron import utils as neutron_utils
from rally.utils import sshutils
from rally.task import scenario
from rally.task import types
from rally.task import validation


LOG = logging.getLogger(__name__)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("number", param_name="port", minval=1, maxval=65535,
                nullable=True, integer_only=True)
@validation.add("external_network_exists", param_name="floating_network")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_param_or_context",
                param_name="image", ctx_name="image_command_customizer")
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.stress_ng",
                    platform="openstack")
class BrowbeatStressNg(vm_utils.VMScenario, neutron_utils.NeutronScenario):

    def run(self, flavor, username, ssh_timeout, num_clients,
            command, image=None, floating_network=None, port=22,
            use_floating_ip=True, **kwargs):
        """Create a jumphost on network with fip and all
           other vm's on the same neutron network so that jumphost
           can access the other vm's and run the stress tests

        :param flavor: VM flavor name
        :param username: ssh username on server
        :param ssh_timeout: ssh timeout in seconds
        :param num_clients: no.of clients
        :param command: command that runs inside the client vm's
        :param floating_network: external network name, for floating ip
        :param port: ssh port for SSH connection
        :param use_floating_ip: bool, floating or fixed IP for SSH connection
        :param kwargs: optional args to create a VM
        """
        jump_host, fip = self._boot_server_with_fip(
            image, flavor, use_floating_ip=use_floating_ip,
            floating_network=floating_network,
            key_name=self.context["user"]["keypair"]["name"],
            **kwargs)
        ssh = sshutils.SSH(username, fip["ip"], port=port, pkey=self.context[
                           "user"]["keypair"]["private"])
        self._wait_for_ssh(ssh, timeout=ssh_timeout)

        # Write id_rsa to get to guests.
        self._run_command_over_ssh(ssh, {'remote_path': "rm -rf ~/.ssh"})
        self._run_command_over_ssh(ssh, {'remote_path': "mkdir ~/.ssh"})
        ssh.run(
            "cat > ~/.ssh/id_rsa",
            stdin=self.context["user"]["keypair"]["private"])
        ssh.execute("chmod 0600 ~/.ssh/id_rsa")

        _clients = self.create_clients(
            ssh, num_clients, image, flavor, username, **kwargs)

        # Run stress test
        for sip in _clients:
            cmd = " {} 'ssh {}@{}' ".format(command, username, sip)
            exitcode, stdout, stderr = ssh.execute(cmd)
            LOG.error(" couldn't run the stress-ng command: {}".format(stderr))

    def create_clients(self, jump_ssh, num_clients, image, flavor, user, **kwargs):
        """Creates Client VM's

        :param jump_ssh: ssh connection
        :param num_clients: no.of clients
        :param image: VM image name
        :param flavor: VM flavor name
        :param user: ssh username on server
        :param kwargs: optional args to create a VM
        """
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

            for sip in _clients:
                cmd = "ssh -o StrictHostKeyChecking=no {}@{} /bin/true".format(
                    user, sip)
                s1_exitcode, s1_stdout, s1_stderr = jump_ssh.execute(cmd)
        return _clients

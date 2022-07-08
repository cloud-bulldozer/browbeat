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
                    name="BrowbeatPlugin.create_network_nova_boot_test_metadata",
                    platform="openstack")
class CreateNetworkNovaBootTestMetadata(vm_utils.VMScenario):

    def run(self, flavor, username, ssh_timeout, image=None, floating_network=None,
            port=22, use_floating_ip=True, **kwargs):
        """Boot a server, to test metadata
        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param username: ssh username on server, str
        :param ssh_timeout: wait for ssh timeout. Default is 120 seconds
        :param floating_network: external network name, for floating ip
        :param port: ssh port for SSH connection
        :param use_floating_ip: bool, floating or fixed IP for SSH connection
        :param kwargs: Optional additional arguments for server creation
        """

        if not image:
            image = self.context["tenant"]["custom_image"]["id"]

        server, fip = self._boot_server_with_fip(
            image, flavor, use_floating_ip=use_floating_ip,
            floating_network=floating_network,
            key_name=self.context["user"]["keypair"]["name"],
            **kwargs)
        ssh = sshutils.SSH(username, fip["ip"], port=port, pkey=self.context[
                           "user"]["keypair"]["private"])
        self._wait_for_ssh(ssh, timeout=ssh_timeout)

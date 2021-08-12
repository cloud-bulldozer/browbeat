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

import time

from rally.common import cfg
from rally.common import logging
from rally_openstack.scenarios.vm import utils as vm_utils
from rally.task import atomic
from rally.task import utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class NovaDynamicScenario(vm_utils.VMScenario):

    def _run_command_with_attempts(self, ssh_connection, cmd, max_attempts=120, timeout=2):
        """Run command over ssh connection with multiple attempts
        :param ssh_connection: ssh connection to run command
        :param cmd: command to run
        :param max_attempts: int, maximum number of attempts to retry command
        :param timeout: int, maximum time to wait for command to complete
        """
        attempts = 0
        while attempts < max_attempts:
            status, out, err = ssh_connection.execute(cmd)
            LOG.info("attempt: {} cmd: {}, status:{}".format(
                attempts, cmd, status))
            if status != 0:
                attempts += 1
                time.sleep(timeout)
            else:
                break
        if (attempts == max_attempts) and (status != 0):
            LOG.info(
                "Error running command %(command)s. "
                "Error %(code)s: %(error)s" %
                {"command": cmd, "code": status, "error": err})
        else:
            LOG.info("Command executed successfully: %(command)s" % {"command": cmd})

    def _boot_server_with_tag(self, image, flavor, tag,
                              auto_assign_nic=False, **kwargs):
        """Boot a server with a tag.
        Returns when the server is actually booted and in "ACTIVE" state.
        If multiple networks created by Network context are present, the first
        network found that isn't associated with a floating IP pool is used.
        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param tag: str, tag for server creation
        :param auto_assign_nic: bool, whether or not to auto assign NICs
        :param kwargs: other optional parameters to initialize the server
        :returns: nova Server instance
        """
        server_name = self.generate_random_name()
        secgroup = self.context.get("user", {}).get("secgroup")
        if secgroup:
            if "security_groups" not in kwargs:
                kwargs["security_groups"] = [secgroup["name"]]
            elif secgroup["name"] not in kwargs["security_groups"]:
                kwargs["security_groups"].append(secgroup["name"])

        if auto_assign_nic and not kwargs.get("nics", False):
            nic = self._pick_random_nic()
            if nic:
                kwargs["nics"] = nic

        if "nics" not in kwargs and\
                "tenant" in self.context and\
                "networks" in self.context["tenant"]:
            kwargs["nics"] = [
                {"net-id": self.context["tenant"]["networks"][0]["id"]}]

        for nic in kwargs.get("nics", []):
            if not nic.get("net-id") and nic.get("net-name"):
                nic["net-id"] = self._get_network_id(nic["net-name"])

        kwargs["tags"] = [tag]

        with atomic.ActionTimer(self, "nova.boot_server"):
            server = self.clients("nova", version="2.52").servers.create(
                server_name, image, flavor, **kwargs)

            self.sleep_between(CONF.openstack.nova_server_boot_prepoll_delay)
            server = utils.wait_for_status(
                server,
                ready_statuses=["ACTIVE"],
                update_resource=utils.get_from_manager(),
                timeout=CONF.openstack.nova_server_boot_timeout,
                check_interval=CONF.openstack.nova_server_boot_poll_interval
            )
        return server

    def _boot_server_with_fip_and_tag(self, image, flavor, tag, use_floating_ip=True,
                                      floating_network=None, **kwargs):
        """Boot server prepared for SSH actions, with tag
        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param tag: str, tag for server creation
        :param use_floating_ip: bool, option to assign floating ip
        :param floating_network: external network to attach floating ip
        :param kwargs: other optional parameters to initialize the server
        :returns: nova Server instance, dict with floating ip details
        """
        kwargs["auto_assign_nic"] = True
        server = self._boot_server_with_tag(image, flavor, tag, **kwargs)

        if not server.networks:
            raise RuntimeError(
                "Server `%s' is not connected to any network. "
                "Use network context for auto-assigning networks "
                "or provide `nics' argument with specific net-id." %
                server.name)

        if use_floating_ip:
            fip = self._attach_floating_ip(server, floating_network)
        else:
            internal_network = list(server.networks)[0]
            fip = {"ip": server.addresses[internal_network][0]["addr"]}

        return server, {"ip": fip.get("ip"),
                        "id": fip.get("id"),
                        "is_floating": use_floating_ip}

    def _get_servers_by_tag(self, tag):
        """Retrieve list of servers based on tag.
        :param tag: str, tag to search for
        :returns: list of server objects based on tag
        """
        return self.clients("nova", version="2.52").servers.list(
            search_opts={'tags': tag, 'status': "ACTIVE"})

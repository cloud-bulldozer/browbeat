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

from rally.common import cfg
from rally.common import sshutils

from rally_openstack.scenarios.vm import utils as vm_utils
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally.task import atomic
from rally.task import utils

from browbeat_rally.db import api as db_api
from oslo_db import exception as db_exc

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
logging.getLogger("paramiko").setLevel(logging.WARNING)


class NovaUtils(vm_utils.VMScenario):

    def log_info(self, msg):
        """Log information with iteration number
        :param msg: str, message to log
        """
        log_msg = " DYNAMIC_WORKLOADS ITER: {} {} ".format(self.context["iteration"], msg)
        LOG.info(log_msg)

    def log_error(self, msg):
        """Log error with iteration number
        :param msg: str, message to log
        """
        log_msg = " DYNAMIC_WORKLOADS ITER: {} {} ".format(self.context["iteration"], msg)
        LOG.error(log_msg)

    def get_ssh(self, user, ip, password=None, timeout=300, interval=5):
        if password:
            ssh = sshutils.SSH(user, ip, password=password)
        else:
            ssh = sshutils.SSH(user, ip, pkey=self.context["user"]["keypair"]["private"])

        self._wait_for_ssh(ssh, timeout=timeout, interval=interval)
        return ssh

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
            self.log_info("attempt: {} cmd: {}, status:{}".format(
                attempts, cmd, status))
            if status != 0:
                attempts += 1
                time.sleep(timeout)
            else:
                break
        if (attempts == max_attempts) and (status != 0):
            self.log_info(
                "Error running command %(command)s. "
                "Error %(code)s: %(error)s" %
                {"command": cmd, "code": status, "error": err})
        else:
            self.log_info("Command executed successfully: %(command)s" % {"command": cmd})

    def _run_command_until_failure(self, ssh_connection, cmd, timeout=2):
        """Run command over ssh connection until failure
        :param ssh_connection: ssh connection to run command
        :param cmd: command to run
        :param timeout: int, maximum time to wait for command to complete
        """
        while True:
            status, out, err = ssh_connection.execute(cmd)
            self.log_info("cmd: {}, status:{}".format(cmd, status))
            if status == 0:
                time.sleep(timeout)
            else:
                break

    def assign_ping_fip_from_jumphost(self, jumphost_fip, jumphost_user,
                                      fip, port_id, success_on_ping_failure=False):
        """Ping floating ip from jumphost
        :param jumphost_fip: floating ip of jumphost
        :param jumphost_user: str, ssh user for jumphost
        :param fip: floating ip of port
        :param port_id: id of port to ping from jumphost
        :param success_on_ping_failure: bool, flag to ping till failure/success
        """
        if not(success_on_ping_failure):
            fip_update_dict = {"port_id": port_id}
            self.clients("neutron").update_floatingip(
                fip["id"], {"floatingip": fip_update_dict}
            )

        address = fip["floating_ip_address"]
        jumphost_ssh = self.get_ssh(jumphost_user, jumphost_fip)
        cmd = f"ping -c1 -w1 {address}"
        if success_on_ping_failure:
            self._run_command_until_failure(jumphost_ssh, cmd)
        else:
            self._run_command_with_attempts(jumphost_ssh, cmd)

    @atomic.action_timer("vm.wait_for_ping_failure")
    def _wait_for_ping_failure(self, server_ip):
        """Wait for ping failure to floating IP of server
        :param server_ip: floating IP of server
        """
        server = vm_utils.Host(server_ip)
        utils.wait_for_status(
            server,
            ready_statuses=[vm_utils.Host.ICMP_DOWN_STATUS],
            update_resource=vm_utils.Host.update_status,
            timeout=CONF.openstack.vm_ping_timeout,
            check_interval=CONF.openstack.vm_ping_poll_interval
        )

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

        # Each iteration has a unique security group for its resources
        if self.security_group:
            if "security_groups" not in kwargs:
                kwargs["security_groups"] = [self.security_group["name"]]
            elif self.security_group["name"] not in kwargs["security_groups"]:
                kwargs["security_groups"].append(self.security_group["name"])

        # Let every 5th iteration add default security group of the tenant/user
        secgroup = self.context.get("user", {}).get("secgroup")
        if secgroup and (self.context["iteration"] % 5):
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

    def _get_fip_by_server(self, server):
        """Check if server has floating IP, and retrieve it if it does
        :param server: server object to check for floating IP
        :returns: floating IP address of server, or False
        """
        try:
            fip = list(server.addresses.values())[0][1]['addr']
            return fip
        except IndexError:
            return False

    def show_server(self, server):
        """Show server details
        :param server: server object to get details for
        :returns: server details
        """
        return self.clients("nova", version="2.52").servers.get(server)


class NeutronUtils(neutron_utils.NeutronScenario):

    def log_info(self, msg):
        """Log information with iteration number
        :param msg: str, message to log
        """
        log_msg = " DYNAMIC_WORKLOADS ITER: {} {} ".format(self.context["iteration"], msg)
        LOG.info(log_msg)

    def log_error(self, msg):
        """Log error with iteration number
        :param msg: str, message to log
        """
        log_msg = " DYNAMIC_WORKLOADS ITER: {} {} ".format(self.context["iteration"], msg)
        LOG.error(log_msg)

    @atomic.action_timer("neutron.create_router")
    def _create_router(self, router_create_args):
        """Create neutron router.
        :param router_create_args: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        return self.admin_clients("neutron").create_router(
            {"router": router_create_args}
        )

    def dissociate_and_delete_floating_ip(self, fip_id):
        """Dissociate and delete floating IP of port
        :param fip_id: id of floating IP of subport
        """
        fip_update_dict = {"port_id": None}
        self.clients("neutron").update_floatingip(
            fip_id, {"floatingip": fip_update_dict}
        )
        self.clients("neutron").delete_floatingip(fip_id)

    def create_floating_ip_and_associate_to_port(self, port, ext_net_name):
        """Create and associate floating IP for port
        :param port: port object to create floating IP
        :param ext_net_name: name of external network to create floating IP
        :returns: floating IP for port
        """
        port_fip = self._create_floatingip(ext_net_name)["floatingip"]
        fip_update_dict = {"port_id": port["port"]["id"]}
        self.clients("neutron").update_floatingip(
            port_fip["id"], {"floatingip": fip_update_dict}
        )
        return port_fip

    def _create_sec_group_rule(self, security_group, protocol):
        """Create rule for security group
        :param security_group: security group object to create rule
        :param protocol: str, protocol of rule to create
        """
        security_group_rule_args = {}
        security_group_rule_args["security_group_id"] = security_group["security_group"]["id"]
        security_group_rule_args["direction"] = "ingress"
        security_group_rule_args["remote_ip_prefix"] = "0.0.0.0/0"
        security_group_rule_args["protocol"] = protocol
        if protocol == "tcp":
            security_group_rule_args["port_range_min"] = 22
            security_group_rule_args["port_range_max"] = 22
        self.clients("neutron").create_security_group_rule(
            {"security_group_rule": security_group_rule_args})

    def create_sec_group_with_icmp_ssh(self):
        """Create security group with icmp and ssh rules
        :returns: security group dict
        """
        security_group_args = {}
        security_group_args["name"] = self.generate_random_name()
        security_group = self.clients("neutron").create_security_group(
            {"security_group": security_group_args})
        self._create_sec_group_rule(security_group, "icmp")
        self._create_sec_group_rule(security_group, "tcp")
        return security_group["security_group"]

    def show_router(self, router_id, **kwargs):
        """Show information of a given router
        :param router_id: ID of router to look up
        :kwargs: dict, POST /v2.0/routers show options
        :returns: details of the router
        """
        return self.admin_clients("neutron").show_router(router_id, **kwargs)

    def show_network(self, network_id, **kwargs):
        """Show information of a given network
        :param network_id: ID of network to look up
        :kwargs: dict, POST /v2.0/networks show options
        :returns: details of the network
        """
        return self.admin_clients("neutron").show_network(network_id, **kwargs)

    def show_subnet(self, subnet_id):
        """Show information of a given subnet
        :param subnet_id: ID of subnet to look up
        :returns: details of the subnet
        """
        return self.admin_clients("neutron").show_subnet(subnet_id)

    def get_router_from_context(self):
        """Retrieve router that was created as part of Rally context
        :returns: router object that is part of Rally context
        """
        return self.show_router(self.context["tenant"]["networks"][0]["router_id"])

    def get_network_from_context(self):
        """Retrieve network that was created as part of Rally context
        :returns: network object that is part of Rally context
        """
        return self.show_network(self.context["tenant"]["networks"][0]["id"])

    def get_subnet_from_context(self):
        """Retrieve subnet that was created as part of Rally context
        :returns: subnet object that is part of Rally context
        """
        return self.show_subnet(self.context["tenant"]["networks"][0]["subnets"][0])

class LockUtils:

    def acquire_lock(self, object_id):
        """Acquire lock on object
        :param object_id: id of object to lock
        :returns: bool, whether the lock was acquired successfully or not
        """
        try:
            db_api.get_lock(object_id)
            return True
        except db_exc.DBDuplicateEntry:
            return False

    def list_locks(self):
        """List all locks in database
        :returns: list, list of lock dictionaries
        """
        return db_api.lock_list()

    def release_lock(self, object_id):
        """Release lock on object
        :param object_id: id of object to release lock from
        """
        db_api.release_lock(object_id)

    def cleanup_locks(self):
        """Release all locks in database
        """
        locks_list = self.list_locks()
        for lock in locks_list:
            self.release_lock(lock["lock_uuid"])

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

from random import randint
from rally_openstack import consts
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally_openstack.scenarios.vm import utils as vm_utils
from rally.task import atomic
from rally.task import scenario
from rally.task import types
from rally.task import validation


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"], "keypair@openstack": {},
                             "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.create_network_nova_boot_ping_sec_groups",
                    platform="openstack")
class CreateNetworkNovaBootPingSecGroups(vm_utils.VMScenario,
                                         neutron_utils.NeutronScenario):

    def run(self, image, flavor, ext_net_id, num_vms=1, num_sg=1, num_sgr=2,
            router_create_args=None, network_create_args=None,
            subnet_create_args=None, **kwargs):
        ext_net_name = None
        if ext_net_id:
            ext_net_name = self.clients("neutron").show_network(
                ext_net_id)["network"]["name"]
        router_create_args["name"] = self.generate_random_name()
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault("external_gateway_info",
                                      {"network_id": ext_net_id, "enable_snat": True})
        router = self._create_router(router_create_args)

        network = self._create_network(network_create_args or {})
        subnet = self._create_subnet(network, subnet_create_args or {})
        self._add_interface_router(subnet['subnet'], router['router'])

        security_groups = [self._create_security_group_icmp_ssh()]
        # All the VMs will be part of both remote_security_group and the
        # security group with rules we are creating here
        for sg in range(num_sg):
            security_group_remote = self._create_remote_security_group()
            security_groups.append(security_group_remote)
            security_groups.append(self._create_security_group_random_rules(
                num_sgr, security_group_remote["security_group"]["id"]))

        for i in range(num_vms):
            kwargs["nics"] = [{'net-id': network['network']['id']}]
            kwargs["security_groups"] = [sg["security_group"]["name"]
                                         for sg in security_groups]
            guest = self._boot_server_with_fip(image, flavor, True,
                                               ext_net_name, **kwargs)
            self._wait_for_ping(guest[1]['ip'])

    def _create_remote_security_group(self):
        """Create neutron remote security group.

        :param none
        :returns: neutron security group object
        """
        security_group_args = {}
        security_group = self._create_security_group(**security_group_args)
        msg = "security_group isn't created"
        self.assertTrue(security_group, err_msg=msg)
        return security_group

    def _create_security_group_random_rules(self, num_sgr, remote_group):
        """Create neutron security group rules.

        :param num_sgr: number of security group rules to create
        :param remote_group: remote security group
        :returns: neutron security group object
        """
        security_group_args = {}
        security_group = self._create_security_group(**security_group_args)
        msg = "security_group isn't created"
        self.assertTrue(security_group, err_msg=msg)
        port_range_start = randint(1000, 60000)
        port_range_end = port_range_start + num_sgr
        for port_range in range(port_range_start, port_range_end):
            security_group_rule_args = {}
            if (port_range % 2) == 0:
                security_group_rule_args["protocol"] = "tcp"
            else:
                security_group_rule_args["protocol"] = "udp"
            security_group_rule_args["port_range_min"] = port_range
            security_group_rule_args["port_range_max"] = port_range
            security_group_rule_args["remote_group_id"] = remote_group
            security_group_rule = self._create_security_group_rule(
                security_group["security_group"]["id"],
                **security_group_rule_args)
            msg = "security_group_rule isn't created"
            self.assertTrue(security_group_rule, err_msg=msg)
        return security_group

    def _create_security_group_icmp_ssh(self):
        """Create neutron security group for icmp and ssh.

        :param none
        :returns: neutron security group object
        """
        security_group_args = {}
        security_group = self._create_security_group(**security_group_args)
        msg = "security_group isn't created"
        self.assertTrue(security_group, err_msg=msg)
        for protocol in ["icmp", "tcp"]:
            security_group_rule_args = {}
            if protocol == "icmp":
                security_group_rule_args["protocol"] = "icmp"
                security_group_rule_args["remote_ip_prefix"] = "0.0.0.0/0"
            else:
                security_group_rule_args["protocol"] = "tcp"
                security_group_rule_args["port_range_min"] = 22
                security_group_rule_args["port_range_max"] = 22
            security_group_rule = self._create_security_group_rule(
                security_group["security_group"]["id"],
                **security_group_rule_args)
            msg = "security_group_rule isn't created"
            self.assertTrue(security_group_rule, err_msg=msg)
        return security_group

    @atomic.action_timer("neutron.create_router")
    def _create_router(self, router_create_args):
        """Create neutron router.

        :param router_create_args: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        return self.admin_clients("neutron").create_router({"router": router_create_args})

#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from rally_openstack import consts
from rally_openstack.scenarios.cinder import utils as cinder_utils
from rally_openstack.scenarios.vm import utils as vm_utils
from rally_openstack.task.scenarios.neutron import utils as neutron_utils

from rally.task import scenario
from rally.task import types
from rally.task import validation


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("restricted_parameters", param_names=["name", "display_name"],
                subdict="create_volume_params")
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder", "nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.create_vm_attach_and_detach_volume", platform="openstack")
class CreateVmAttachAndDetachVolume(vm_utils.VMScenario, neutron_utils.NeutronScenario,
                                    cinder_utils.CinderBasic,):

    def run(self, size, image, flavor, ext_net_id, router_create_args,
            network_create_args=None, subnet_create_args=None,
            create_volume_params={}, **kwargs):

        ext_net_name = self.clients("neutron").show_network(
            ext_net_id)["network"]["name"]
        router_create_args["name"] = self.generate_random_name()
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault("external_gateway_info",
                                      {"network_id": ext_net_id, "enable_snat": True})
        router = self.admin_clients("neutron").create_router({"router": router_create_args})

        network = self._create_network(network_create_args or {})
        subnet = self._create_subnet(network, subnet_create_args or {})
        self._add_interface_router(subnet['subnet'], router['router'])
        kwargs["nics"] = [{'net-id': network['network']['id']}]
        security_group = self._create_security_group_icmp_ssh()
        kwargs["security_groups"] = [security_group["security_group"]["name"]]

        guest = self._boot_server_with_fip(
            image, flavor, True,
            floating_network=ext_net_name,
            key_name=self.context["user"]["keypair"]["name"],
            **kwargs)
        server_fip = guest[1]['ip']
        self._wait_for_ping(server_fip)

        volume = self.cinder.create_volume(size, **create_volume_params)
        server = self._show_server(guest[0])

        self._attach_volume(server, volume)
        self._detach_volume(server, volume)
        self.cinder.delete_volume(volume)
        self._delete_server_with_fip(guest[0], guest[1])

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

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

from rally.common import logging
from rally import exceptions
from rally.task import types
from rally.task import utils as rally_utils
from rally.task import validation
from rally.task import scenario

from rally_openstack.common import consts
from rally_openstack.task.scenarios.manila import utils
from rally_openstack.task.scenarios.vm import utils as vm_utils
from rally_openstack.task.scenarios.neutron import utils as neutron_utils

"""Scenarios for Manila shares."""

LOG = logging.getLogger(__name__)

@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image", fail_on_404_image=False)
@validation.add("number", param_name="port", minval=1, maxval=65535,
                nullable=True, integer_only=True)
@validation.add("external_network_exists", param_name="floating_network")
@validation.add("required_services", services=[consts.Service.MANILA,
                                               consts.Service.NEUTRON,
                                               consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["manila", "nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.create_share_boot_vm_access_share",
                    platform="openstack")
class CreateNFSShareBootVMAndAccessShare(utils.ManilaScenario, vm_utils.VMScenario,
                                         neutron_utils.NeutronScenario):
    def run(self, image, flavor, username, provider_net_id, ext_net_id, size=1, password=None,
            router_create_args=None, network_create_args=None, subnet_create_args=None,
            port=22, use_floating_ip=True, force_delete=False, max_log_length=None,
            **kwargs):
        """Create a share and access it from VM.

        - create NFS share
        - launch VM
        - Attach provider network (StorageNFS) to VM
        - authorize VM's ip (StorageNFS) to access the share
        - mount share inside the VM
        - write to share
        - delete VM
        - delete share

        :param size: share size in GB, should be greater than 0
        :param image: glance image name to use for the vm
        :param flavor: VM flavor name
        :param username: ssh username on server
        :param provider_net_id: ID of the StorageNFS provider network
        :param ext_net_id: ID of external network
        :param password: Password on SSH authentication
        :param floating_network: external network name, for floating ip
        :param port: ssh port for SSH connection
        :param use_floating_ip: bool, floating or fixed IP for SSH connection
        :param force_delete: whether to use force_delete for servers
        :param max_log_length: The number of tail nova console-log lines user
                               would like to retrieve
        :param kwargs: optional args to create a share or a VM
        """
        share_proto = "nfs"
        share = self._create_share(
            share_proto=share_proto,
            size=size,
            **kwargs)
        location = self._export_location(share)

        ext_net_name = self.clients("neutron").show_network(
            ext_net_id)["network"]["name"]
        router_create_args["tenant_id"] = self.context["tenant"]["id"]
        router_create_args.setdefault("external_gateway_info",
                                      {"network_id": ext_net_id, "enable_snat": True})
        router = self.admin_clients("neutron").create_router({"router": router_create_args})

        network = self._create_network(network_create_args or {})
        subnet = self._create_subnet(network, subnet_create_args or {})
        self._add_interface_router(subnet['subnet'], router['router'])
        kwargs["nics"] = [{"net-id": network['network']['id']}]

        server, fip = self._boot_server_with_fip(
            image, flavor, use_floating_ip=use_floating_ip,
            floating_network=ext_net_name,
            key_name=self.context["user"]["keypair"]["name"],
            **kwargs)
        self._attach_interface(server, net_id=provider_net_id)
        server = self._show_server(server)

        for net in server.addresses:
            if str(net) == self.clients("neutron").show_network(provider_net_id)["network"]["name"]:
                ip = str(server.addresses[net][0]["addr"])
                self._allow_access_share(share, "ip", ip, "rw")

        mount_opt = "-t nfs -o nfsvers=4.1,proto=tcp"
        test_data = "Test Data"
        script = f"sudo cloud-init status -w && " \
            f"sudo ip add add {ip}/24 dev eth1 && " \
            f"sudo ip link set eth1 up && " \
            f"sudo mount {mount_opt} {location[0]} /mnt || exit 1 && " \
            f"df -h && " \
            f"sudo echo {test_data} | sudo tee /mnt/testfile || exit 2"

        command = {
            "script_inline": script,
            "interpreter": "/bin/bash"
        }
        try:
            rally_utils.wait_for_status(
                server,
                ready_statuses=["ACTIVE"],
                update_resource=rally_utils.get_from_manager(),
            )

            code, out, err = self._run_command(
                fip["ip"], port, username, password, command=command)
            if code:
                raise exceptions.ScriptError(
                    "Error running command %(command)s. "
                    "Error %(code)s: %(error)s" % {
                        "command": command, "code": code, "error": err})
        except (exceptions.TimeoutException,
                exceptions.SSHTimeout):
            console_logs = self._get_server_console_output(server,
                                                           max_log_length)
            LOG.debug("VM console logs:\n%s" % console_logs)
            raise

        finally:
            self._delete_server_with_fip(server, fip,
                                         force_delete=force_delete)
            self._delete_share(share)
            self._remove_interface_router(subnet['subnet'], router['router'])

        self.add_output(complete={
            "title": "Script StdOut",
            "chart_plugin": "TextArea",
            "data": str(out).split("\n")
        })
        if err:
            self.add_output(complete={
                "title": "Script StdErr",
                "chart_plugin": "TextArea",
                "data": err.split("\n")
            })

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

from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
from rally.common import sshutils
from rally.task import scenario
from rally.task import types
from rally.task import validation
from rally import consts

LOG = logging.getLogger(__name__)

@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.sysbench", platform="openstack")
class BrowbeatSysbench(neutron_utils.NeutronScenario,vm_utils.VMScenario):
    def build_host(self, external, image, flavor, user, password=None, **kwargs):
        keyname = self.context["user"]["keypair"]["name"]
        host, host_ip = self._boot_server_with_fip(image,
                                                   flavor,
                                                   use_floating_ip=True,
                                                   floating_network=external[
                                                       'name'],
                                                   key_name=keyname,
                                                   **kwargs)
        # Wait for ping
        self._wait_for_ping(host_ip['ip'])

        # Open SSH Connection
        host_ssh = sshutils.SSH(user, host_ip['ip'], 22, self.context[
                                "user"]["keypair"]["private"], password)

        # Check for connectivity
        self._wait_for_ssh(host_ssh)

        return host_ssh, host_ip, host

    def run(self, image, flavor, user, test_name, cpu_max_prime=10000, external=None,
            password="", network_id=None, **kwargs):

        sysbench_path = "/opt/sysbench"

        if not network_id:
            router = self._create_router({}, external_gw=external)
            network = self._create_network({})
            subnet = self._create_subnet(network, {})
            kwargs["nics"] = [{'net-id': network['network']['id']}]
            self._add_interface_router(subnet['subnet'], router['router'])
        else:
            kwargs["nics"] = [{'net-id': network_id}]

        host_ssh, host_ip, host = self.build_host(
            external, image, flavor, user, **kwargs)
        cmd = "cd {}".format(sysbench_path)
        LOG.info("Running command : {}".format(cmd))
        exitcode, stdout, stderr = host_ssh.execute(cmd)
        if exitcode is 1:
                LOG.error(stderr)
                return False
        if test_name == "cpu":
                sysbench = "sysbench --test=cpu --cpu-max-prime={} run".format(cpu_max_prime)
                sysbench += " | grep '{}' | grep -E -o '[0-9]+([.][0-9]+)?'".format("total time: ")
                LOG.info("Starting sysbench with CPU test")
                LOG.info("Running command : {}".format(sysbench))
                test_exitcode, test_stdout, test_stderr = host_ssh.execute(sysbench)
                if test_exitcode is not 1:
                        LOG.info("Result: {}".format(test_stdout))
                        report = [[cpu_max_prime,float(test_stdout)]]
                        self.add_output(additive={"title": "Sysbench Stats",
                                                  "description": "Sysbench CPU Scenario",
                                                  "chart_plugin": "StatsTable",
                                                  "data": report})
                else:
                        LOG.error(test_stderr)

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

import csv
import datetime
import json
import logging
import StringIO
import time

import browbeat.elastic

from rally.common import sshutils
from rally_openstack import consts
from rally_openstack.scenarios.vm import utils as vm_utils
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally.task import scenario
from rally.task import types
from rally.task import validation


LOG = logging.getLogger(__name__)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services", services=[consts.Service.NEUTRON, consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder", "neutron", "nova"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="BrowbeatPlugin.pbench_uperf", platform="openstack")
class BrowbeatPbenchUperf(neutron_utils.NeutronScenario,
                          vm_utils.VMScenario):

    def build_jump_host(self, external, image, flavor, user, password=None, **kwargs):
        keyname = self.context["user"]["keypair"]["name"]
        jump_host, jump_host_ip = self._boot_server_with_fip(image,
                                                             flavor,
                                                             use_floating_ip=True,
                                                             floating_network=external[
                                                                 'name'],
                                                             key_name=keyname,
                                                             **kwargs)
        # Wait for ping
        self._wait_for_ping(jump_host_ip['ip'])

        # Open SSH Connection
        jump_ssh = sshutils.SSH(user, jump_host_ip['ip'], 22, self.context[
                                "user"]["keypair"]["private"], password)

        # Check for connectivity
        self._wait_for_ssh(jump_ssh)

        # Write id_rsa to get to guests.
        self._run_command_over_ssh(jump_ssh, {'remote_path': "rm -rf ~/.ssh"})
        self._run_command_over_ssh(jump_ssh, {'remote_path': "mkdir ~/.ssh"})
        jump_ssh.run(
            "cat > ~/.ssh/id_rsa",
            stdin=self.context["user"]["keypair"]["private"])

        jump_ssh.execute("chmod 0600 ~/.ssh/id_rsa")
        return jump_ssh, jump_host_ip, jump_host

    def create_guest_pairs(
            self,
            jump_ssh,
            num_pairs,
            image,
            flavor,
            user,
            zones=None,
            **kwargs):
        _servers = []
        _clients = []
        # Launch Guests
        network_name = None
        if num_pairs is 1:
            if zones['server'] != 'None':
                kwargs['availability_zone'] = zones['server']
            server = self._boot_server(
                image,
                flavor,
                key_name=self.context["user"]["keypair"]["name"],
                **kwargs)
            if zones['client'] != 'None':
                kwargs['availability_zone'] = zones['client']
            client = self._boot_server(
                image,
                flavor,
                key_name=self.context["user"]["keypair"]["name"],
                **kwargs)
            for net in server.addresses:
                network_name = net
                break
            if network_name is None:
                return False
            # IP Addresses
            _servers.append(
                str(server.addresses[network_name][0]["addr"]))
            _clients.append(
                str(client.addresses[network_name][0]["addr"]))
        else:
            for i in range(num_pairs):
                if zones['server'] != 'None':
                    kwargs['availability_zone'] = zones['server']
                server = self._boot_server(
                    image,
                    flavor,
                    key_name=self.context["user"]["keypair"]["name"],
                    **kwargs)
                if zones['client'] != 'None':
                    kwargs['availability_zone'] = zones['client']
                client = self._boot_server(
                    image,
                    flavor,
                    key_name=self.context["user"]["keypair"]["name"],
                    **kwargs)

                if network_name is None:
                    # IP Addresses
                    for net in server.addresses:
                        network_name = net
                        break

                if network_name is None:
                    return False

                _servers.append(
                    str(server.addresses[network_name][0]["addr"]))
                _clients.append(
                    str(client.addresses[network_name][0]["addr"]))

        # Check status of guest
        ready = False
        retry = 50
        while (not ready):
            for sip in _servers + _clients:
                cmd = "ssh -o StrictHostKeyChecking=no {}@{} /bin/true".format(
                    user, sip)
                s1_exitcode, s1_stdout, s1_stderr = jump_ssh.execute(cmd)
                if retry < 1:
                    LOG.error(
                        "Error : Issue reaching {} the guests through the Jump host".format(sip))
                    LOG.error(
                        "Console : stdout:{} stderr:{}".format(s1_stdout,s1_stderr))
                    return False
                if s1_exitcode is 0:
                    LOG.info("Server: {} ready".format(sip))
                    ready = True
                else:
                    LOG.info(
                        "Error reaching server: {} error {}".format(
                            sip, s1_stderr))
                    retry = retry - 1
                    time.sleep(10)

        return _clients, _servers

    def run(self, image, flavor, user, test_types, protocols, samples, test_name, external=None,
            send_results=True, num_pairs=1, password="", network_id=None, zones=None,
            message_sizes=None, instances=None, elastic_host=None, elastic_port=None,
            cloudname=None, dns_ip=None, **kwargs):

        pbench_path = "/opt/pbench-agent"
        pbench_results = "/var/lib/pbench-agent"

        # Create env
        if not network_id:
            router = self._create_router({}, external_gw=external)
            network = self._create_network({})
            subnet = self._create_subnet(network, {})
            kwargs["nics"] = [{'net-id': network['network']['id']}]
            self._add_interface_router(subnet['subnet'], router['router'])
        else:
            kwargs["nics"] = [{'net-id': network_id}]

        jump_ssh, jump_host_ip, jump_host = self.build_jump_host(
            external, image, flavor, user, **kwargs)
        _clients, _servers = self.create_guest_pairs(
            jump_ssh, num_pairs, image, flavor, user, zones, **kwargs)

        # Register pbench across FIP
        for sip in _servers + _clients:
            cmd = "{}/util-scripts/pbench-register-tool-set --remote={}".format(
                pbench_path, sip)
            exitcode, stdout, stderr = jump_ssh.execute(cmd)

        # Start uperf against private address
        uperf = "{}/bench-scripts/pbench-uperf --clients={} --servers={} --samples={}".format(
            pbench_path, ','.join(_clients), ','.join(_servers), samples)
        uperf += " --test-types={} --protocols={} --config={}".format(
            test_types,
            protocols,
            test_name)

        if message_sizes is not None:
            uperf += " --message-sizes={}".format(message_sizes)

        if instances is not None:
            uperf += " --instances={}".format(instances)

        # Execute pbench-uperf
        # execute returns, exitcode,stdout,stderr
        LOG.info("Starting Rally - PBench UPerf")
        uperf_exitcode, stdout_uperf, stderr = jump_ssh.execute(uperf,timeout=0)

        # Prepare results
        cmd = "cat {}/uperf_{}*/result.csv".format(pbench_results, test_name)
        exitcode, stdout, stderr = jump_ssh.execute(cmd)
        if exitcode is 1:
            return False

        if send_results:
            if uperf_exitcode is not 1:
                cmd = "cat {}/uperf_{}*/result.json".format(
                    pbench_results, test_name)
                LOG.info("Running command : {}".format(cmd))
                exitcode, stdout_json, stderr = jump_ssh.execute(cmd)
                LOG.info("Result: {}".format(stderr))

                es_ts = datetime.datetime.utcnow()
                config = {
                    'elasticsearch': {
                        'host': elastic_host,
                        'port': elastic_port},
                    'browbeat': {
                        'cloud_name': cloudname,
                        'timestamp': es_ts,
                        'num_pairs': num_pairs}}
                elastic = browbeat.elastic.Elastic(config, 'pbench')
                json_result = StringIO.StringIO(stdout_json)
                json_data = json.load(json_result)
                for iteration in json_data:
                    elastic.index_result(iteration, test_name, 'results/')
            else:
                LOG.error("Error with PBench Results")

            # Parse results
            result = StringIO.StringIO('\n'.join(stdout.split('\n')[1:]))
            creader = csv.reader(result)
            report = []
            for row in creader:
                LOG.info("Row: {}".format(row))
                if len(row) < 1 :
                    continue
                if row[2] is '' or row[3] is '' :
                    continue
                if len(row) >= 3:
                    report.append(
                        ["aggregate.{}".format(row[1]), float(row[2])])
                    report.append(["single.{}".format(row[1]), float(row[3])])
            if len(report) > 0:
                self.add_output(
                    additive={"title": "PBench UPerf Stats",
                              "description": "PBench UPerf Scenario",
                              "chart_plugin": "StatsTable",
                              "axis_label": "Gbps",
                              "label": "Gbps",
                              "data": report})
        if dns_ip:
            cmd = "echo nameserver {}".format(dns_ip)
            self._run_command_over_ssh(jump_ssh, {"remote_path": cmd})
        cmd = "{}/util-scripts/pbench-move-results".format(pbench_path)
        exitcode, stdout, stderr = jump_ssh.execute(cmd)

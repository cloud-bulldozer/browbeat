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

from rally.task import scenario
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.task import types
from rally.task import validation
from rally.common import sshutils
import time
import StringIO
import csv
import sys
import json
import datetime
import logger
from Elastic import Elastic

LOG = logging.getLogger(__name__)

class BrowbeatPlugin(neutron_utils.NeutronScenario,
                     vm_utils.VMScenario,
                     scenario.Scenario):

    @types.convert(image={"type": "glance_image"},
                   flavor={"type": "nova_flavor"})
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova", "neutron", "cinder"],
                                 "keypair": {}, "allow_ssh": {}})
    def nova_create_pbench_uperf(
            self,
            image,
            flavor,
            zones,
            user,
            password,
            test_types,
            protocols,
            samples,
            external,
            test_name,
            send_results=True,
            num_pairs=1,
            elastic_host=None,
            elastic_port=None,
            cloudname=None,
            **kwargs):

        pbench_path = "/opt/pbench-agent"
        pbench_results = "/var/lib/pbench-agent"

        # Create env
        router = self._create_router({}, external_gw=external)
        network = self._create_network({})
        subnet = self._create_subnet(network, {})
        kwargs["nics"] = [{'net-id': network['network']['id']}]
        self._add_interface_router(subnet['subnet'], router['router'])

        # Launch pbench-jump-host
        jh, jip = self._boot_server_with_fip(image,
                                             flavor,
                                             use_floating_ip=True,
                                             floating_network=external['name'],
                                             key_name=self.context["user"]["keypair"]["name"],
                                             **kwargs)

        servers = []
        clients = []
        # Launch Guests
        if num_pairs is 1:
            server = self._boot_server(
                image,
                flavor,
                key_name=self.context["user"]["keypair"]["name"],
                availability_zone=zones['server'],
                **kwargs)
            client = self._boot_server(
                image,
                flavor,
                key_name=self.context["user"]["keypair"]["name"],
                availability_zone=zones['client'],
                **kwargs)

            # IP Addresses
            servers.append(
                str(server.addresses[network['network']['name']][0]["addr"]))
            clients.append(
                str(client.addresses[network['network']['name']][0]["addr"]))
        else:
            for i in range(num_pairs):
                server = self._boot_server(
                    image,
                    flavor,
                    key_name=self.context["user"]["keypair"]["name"],
                    availability_zone=zones['server'],
                    **kwargs)
                client = self._boot_server(
                    image,
                    flavor,
                    key_name=self.context["user"]["keypair"]["name"],
                    availability_zone=zones['client'],
                    **kwargs)

                # IP Addresses
                servers.append(
                    str(server.addresses[network['network']['name']][0]["addr"]))
                clients.append(
                    str(client.addresses[network['network']['name']][0]["addr"]))

        # Wait for ping
        self._wait_for_ping(jip['ip'])

        # Open SSH Connection
        jump_ssh = sshutils.SSH(user, jip['ip'], 22, self.context[
                                "user"]["keypair"]["private"], password)

        # Check for connectivity
        self._wait_for_ssh(jump_ssh)

        # Write id_rsa to get to guests.
        self._run_command_over_ssh(jump_ssh, {'remote_path': "mkdir ~/.ssh"})
        jump_ssh.run(
            "cat > ~/.ssh/id_rsa",
            stdin=self.context["user"]["keypair"]["private"])
        self._run_command_over_ssh(jump_ssh,
                                   {'remote_path': "chmod 0600 ~/.ssh/id_rsa"})

        # Check status of guest
        ready = False
        retry = 5
        while (not ready):
            for sip in servers + clients:
                cmd = "ssh -o StrictHostKeyChecking=no {}@{} /bin/true".format(
                    user, sip)
                s1_exitcode, s1_stdout, s1_stderr = jump_ssh.execute(cmd)
                if retry < 1:
                    LOG.error("Error : Issue reaching {} the guests through the Jump host".format(sip))
                    return 1
                if s1_exitcode is 0:
                    ready = True
                else:
                    retry = retry - 1
                    time.sleep(5)

        # Register pbench across FIP
        for sip in servers + clients:
            cmd = "{}/util-scripts/pbench-register-tool-set --remote={}".format(
                pbench_path, sip)
            self._run_command_over_ssh(jump_ssh, {'remote_path': cmd})

        # Quick single test
        #debug = "--message-sizes=1024 --instances=1"
        debug = None

        # Start uperf against private address
        uperf = "{}/bench-scripts/pbench-uperf --clients={} --servers={} --samples={} {}".format(
            pbench_path, ','.join(clients), ','.join(servers), samples, debug)
        uperf += " --test-types={} --protocols={} --config={}".format(
            test_types,
            protocols,
            test_name)

        # Execute pbench-uperf
        # execute returns, exitcode,stdout,stderr
        LOG.info("Starting Rally - PBench UPerf")
        exitcode, stdout_uperf, stderr = self._run_command_over_ssh(
            jump_ssh, {"remote_path": uperf})

        # Prepare results
        cmd = "cat {}/uperf_{}*/result.csv".format(pbench_results, test_name)
        exitcode, stdout, stderr = self._run_command_over_ssh(
            jump_ssh, {'remote_path': cmd})

        if send_results and exitcode is not 1:
            cmd = "cat {}/uperf_{}*/result.json".format(
                pbench_results, test_name)
            exitcode, stdout_json, stderr = self._run_command_over_ssh(
                jump_ssh, {'remote_path': cmd})

            es_ts = datetime.datetime.utcnow()
            config = {
                'elasticsearch': {
                    'host': elastic_host, 'port': elastic_port}, 'browbeat': {
                    'cloud_name': cloudname, 'timestamp': es_ts}}
            elastic = Elastic(config, 'pbench')
            json_result = StringIO.StringIO(stdout_json)
            json_data = json.load(json_result)
            for iteration in json_data:
                elastic.index_result(iteration)
        else:
            LOG.error("Error with PBench Results")

        # Parse results
        result = StringIO.StringIO('\n'.join(stdout.split('\n')[1:]))
        creader = csv.reader(result)
        report = []
        for row in creader:
            if len(row) >= 1:
                report.append(["aggregate.{}".format(row[1]), float(row[2])])
                report.append(["single.{}".format(row[1]), float(row[3])])
        if len(report) > 0:
            self.add_output(
                additive={"title": "PBench UPerf Stats",
                          "description": "PBench UPerf Scenario",
                          "chart_plugin": "StatsTable",
                          "axis_label": "Gbps",
                          "label": "Gbps",
                          "data": report})

            cmd = "{}/util-scripts/pbench-move-results".format(pbench_path)
            self._run_command_over_ssh(jump_ssh, {"remote_path": cmd})

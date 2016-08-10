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

from Tools import Tools
from Grafana import Grafana
from WorkloadBase import WorkloadBase
from Elastic import Elastic
from collections import OrderedDict
import yaml
import logging
import datetime
import os
import json
import time
import uuid


class Shaker(WorkloadBase):

    def __init__(self, config):
        self.logger = logging.getLogger('browbeat.Shaker')
        self.config = config
        self.tools = Tools(self.config)
        self.grafana = Grafana(self.config)
        self.elastic = Elastic(self.config, self.__class__.__name__.lower())
        self.error_count = 0
        self.pass_count = 0
        self.test_count = 0
        self.scenario_count = 0

    def shaker_checks(self):
        cmd = "source /home/stack/overcloudrc; glance image-list | grep -w shaker-image"
        if self.tools.run_cmd(cmd) == "":
            self.logger.error("Shaker Image is not built, try again")
            exit(1)
        else:
            self.logger.info("Shaker image is built, continuing")

    def get_stats(self):
        self.logger.info(
            "Current number of Shaker tests executed: {}".format(
                self.test_count))
        self.logger.info(
            "Current number of Shaker tests passed: {}".format(
                self.pass_count))
        self.logger.info(
            "Current number of Shaker tests failed: {}".format(
                self.error_count))

    def final_stats(self, total):
        self.logger.info(
            "Total Shaker scenarios enabled by user: {}".format(total))
        self.logger.info(
            "Total number of Shaker tests executed: {}".format(
                self.test_count))
        self.logger.info(
            "Total number of Shaker tests passed: {}".format(self.pass_count))
        self.logger.info(
            "Total number of Shaker tests failed: {}".format(self.error_count))

    def update_tests(self):
        self.test_count += 1

    def update_pass_tests(self):
        self.pass_count += 1

    def update_fail_tests(self):
        self.error_count += 1

    def update_scenarios(self):
        self.scenario_count += 1

    # Method to process JSON outputted by Shaker, model data in a format that can be consumed
    # by ElasticSearch and ship the data to ES

    def send_to_elastic(self, outputfile, browbeat_scenario, shaker_uuid):
        es_ts = datetime.datetime.utcnow()
        es_list = []
        fname = outputfile
        # Load output json
        try:
            with open(fname) as data_file:
                data = json.load(data_file)
        # If output JSON doesn't exist, ship UUID of failed run to ES
        except IOError:
            self.logger.error(
                "The Shaker output JSON could not be found, pushing details to Elastic")
            record = {'status': "error"}
            shaker_stats = {
                'timestamp': str(es_ts).replace(" ", "T"),
                'browbeat_scenario': browbeat_scenario,
                'shaker_uuid': str(shaker_uuid),
                'record': record
            }

            result = self.elastic.combine_metadata(shaker_stats)
            self.elastic.index_result(result)
            return
        # Dictionary to capture common test data
        shaker_test_meta = {}
        for scenario in data['scenarios'].iterkeys():
            test_time = data['scenarios'][scenario][
                'execution']['tests'][0]['time']
            # Setting up the timestamp list based on the time the test ran for
            for interval in range(0, test_time + 9):
                es_list.append(
                    datetime.datetime.utcnow() +
                    datetime.timedelta(
                        0,
                        interval))
            # Populating common test data
            if 'shaker_test_info' not in shaker_test_meta:
                shaker_test_meta['shaker_test_info'] = data[
                    'scenarios'][scenario]
                if "progression" not in shaker_test_meta[
                        'shaker_test_info']['execution']:
                    shaker_test_meta['shaker_test_info']['execution']['progression'] = "all"
                var = data['scenarios'][scenario][
                    'deployment'].pop('accommodation')
            if 'deployment' not in shaker_test_meta:
                shaker_test_meta['deployment'] = {}
                shaker_test_meta['deployment']['accommodation'] = {}
                shaker_test_meta['deployment'][
                    'accommodation']['distribution'] = var[0]
                shaker_test_meta['deployment'][
                    'accommodation']['placement'] = var[1]
                shaker_test_meta['deployment']['accommodation'][
                    'density'] = var[2]['density']
                shaker_test_meta['deployment']['accommodation'][
                    'compute_nodes'] = var[3]['compute_nodes']
                shaker_test_meta['deployment']['template'] = data[
                    'scenarios'][scenario]['deployment']['template']
        # Iterating through each record to get result values
        for record in data['records'].iterkeys():
            if data['records'][record]['status'] == "ok":
                if 'stdout' in data['records'][record]:
                    del data['records'][record]['stdout']
                metadata = data['records'][record].pop('meta')
                samples = data['records'][record].pop('samples')
                # Ordered Dictionary to capture result types and metrics
                outputs = OrderedDict()
                for metric in metadata:
                    outputs[metric[0]] = metric[1]
                # Iterate over each result type for each sample in record and
                # get associated value
                for key in outputs.iterkeys():
                    if key == "time":
                        continue
                    # Iterate in step lock over each list of samples in the
                    # samples list wrt timestamp
                    for sample, es_time in zip(samples, es_list):
                        elastic_timestamp = str(es_time).replace(" ", "T")
                        result = {}
                        shaker_stats = {}
                        result['value'] = sample[outputs.keys().index(key)]
                        result['metric'] = outputs[key]
                        result['result_type'] = key
                        # Populate shaker_stats dictionary with individual result value from the
                        # list of samples for each test type(tcp download/ping_icm) for each
                        # record afterrecord after flattening out data
                        shaker_stats = {
                            'record': data['records'][record],
                            'shaker_test_info': shaker_test_meta['shaker_test_info'],
                            'timestamp': elastic_timestamp,
                            'accommodation': shaker_test_meta['deployment']['accommodation'],
                            'template': shaker_test_meta['deployment']['template'],
                            'result': result,
                            'browbeat_scenario': browbeat_scenario,
                            'grafana_url': [self.grafana.grafana_urls()],
                            'shaker_uuid': str(shaker_uuid)}
                        # Ship Data to Es when record status is ok
                        result = self.elastic.combine_metadata(shaker_stats)
                        self.elastic.index_result(result)
            else:
                # If the status of the record is not ok, ship minimal
                # shaker_stats dictionary to ES
                shaker_stats = {
                    'record': data['records'][record],
                    'shaker_test_info': shaker_test_meta['shaker_test_info'],
                    'timestamp': str(es_ts).replace(" ", "T"),
                    'accommodation': shaker_test_meta['deployment']['accommodation'],
                    'template': shaker_test_meta['deployment']['template'],
                    'browbeat_scenario': browbeat_scenario,
                    'grafana_url': [self.grafana.grafana_urls()],
                    'shaker_uuid': str(shaker_uuid)}
                result = self.elastic.combine_metadata(shaker_stats)
                self.elastic.index_result(result)

    def set_scenario(self, scenario, fname):
        stream = open(fname, 'r')
        data = yaml.load(stream)
        stream.close()
        default_placement = "double_room"
        default_density = 1
        default_compute = 1
        default_progression = "linear"
        default_time = 60
        if "placement" in scenario:
            data['deployment']['accommodation'][1] = scenario['placement']
        else:
            data['deployment']['accommodation'][1] = default_placement
        if "density" in scenario:
            data['deployment']['accommodation'][
                2]['density'] = scenario['density']
        else:
            data['deployment']['accommodation'][2]['density'] = default_density
        if "compute" in scenario:
            data['deployment']['accommodation'][3][
                'compute_nodes'] = scenario['compute']
        else:
            data['deployment']['accommodation'][3][
                'compute_nodes'] = default_compute
        if "progression" in scenario:
            if scenario['progression'] is None:
                data['execution'].pop('progression', None)
            else:
                data['execution']['progression'] = scenario['progression']
        else:
            data['execution']['progression'] = default_progression
        if "time" in scenario:
            for test in data['execution']['tests']:
                test['time'] = scenario['time']
        else:
            for test in data['execution']['tests']:
                test['time'] = default_time
        with open(fname, 'w') as yaml_file:
            yaml_file.write(yaml.dump(data, default_flow_style=False))

    def get_uuidlist(self, data):
        uuidlist = []
        for key in data['records'].iterkeys():
            uuidlist.append(key)
        return uuidlist

    def result_check(
            self,
            result_dir,
            test_name,
            scenario,
            to_time,
            from_time):
        outputfile = os.path.join(result_dir, test_name + "." + "json")
        error = False
        workload = self.__class__.__name__
        new_test_name = test_name.split('-')
        new_test_name = new_test_name[3:]
        new_test_name = '-'.join(new_test_name)
        try:
            with open(outputfile) as data_file:
                data = json.load(data_file)
        except IOError:
            self.logger.error(
                "Cannot open outputfile, possible stack creation failure for test: {}". format(
                    scenario['name']))
            self.error_update(
                result_dir,
                test_name,
                scenario,
                to_time,
                from_time,
                new_test_name,
                workload)
            return
        uuidlist = self.get_uuidlist(data)
        for id in uuidlist:
            if data['records'][id]['status'] != "ok":
                error = True
        if error:
            self.error_update(
                result_dir,
                test_name,
                scenario,
                to_time,
                from_time,
                new_test_name,
                workload)
        else:
            self.success_update(
                result_dir,
                test_name,
                scenario,
                to_time,
                from_time,
                new_test_name,
                workload)

    def error_update(self, result_dir, test_name, scenario, to_time, from_time,
                     new_test_name, workload):
        self.logger.error("Failed Test: {}".format(scenario['name']))
        self.logger.error(
            "saved log to: {}.log".format(
                os.path.join(
                    result_dir,
                    test_name)))
        self.update_fail_tests()
        self.update_total_fail_tests()
        self.get_time_dict(
            to_time,
            from_time,
            scenario['name'],
            new_test_name,
            workload,
            "fail")

    def success_update(
            self,
            result_dir,
            test_name,
            scenario,
            to_time,
            from_time,
            new_test_name,
            workload):
        self.logger.info("Completed Test: {}".format(scenario['name']))
        self.logger.info(
            "Saved report to: {}.html".format(
                os.path.join(
                    result_dir,
                    test_name)))
        self.logger.info(
            "saved log to: {}.log".format(
                os.path.join(
                    result_dir,
                    test_name)))
        self.update_pass_tests()
        self.update_total_pass_tests()
        self.get_time_dict(
            to_time,
            from_time,
            scenario['name'],
            new_test_name,
            workload,
            "pass")

    def run_scenario(self, scenario, result_dir, test_name, filename):
        server_endpoint = self.config['shaker']['server']
        port_no = self.config['shaker']['port']
        flavor = self.config['shaker']['flavor']
        venv = self.config['shaker']['venv']
        shaker_region = self.config['shaker']['shaker_region']
        timeout = self.config['shaker']['join_timeout']
        shaker_uuid = uuid.uuid4()
        self.logger.info(
            "The uuid for this shaker scenario is {}".format(shaker_uuid))
        cmd_1 = (
            "source {}/bin/activate; source /home/stack/overcloudrc").format(venv)
        cmd_2 = (
            "shaker --server-endpoint {0}:{1} --flavor-name {2} --scenario {3}"
            " --os-region-name {7} --agent-join-timeout {6}"
            " --report {4}/{5}.html --output {4}/{5}.json"
            " --book {4}/{5} --debug > {4}/{5}.log 2>&1").format(
            server_endpoint,
            port_no,
            flavor,
            filename,
            result_dir,
            test_name,
            timeout,
            shaker_region)
        cmd = ("{}; {}").format(cmd_1, cmd_2)
        from_ts = int(time.time() * 1000)
        if 'sleep_before' in self.config['shaker']:
            time.sleep(self.config['shaker']['sleep_before'])
        from_time = time.time()
        self.tools.run_cmd(cmd)
        to_time = time.time()
        self.update_tests()
        self.update_total_tests()
        outputfile = os.path.join(result_dir, test_name + "." + "json")
        self.result_check(result_dir, test_name, scenario, to_time, from_time)
        if 'sleep_after' in self.config['shaker']:
            time.sleep(self.config['shaker']['sleep_after'])
        to_ts = int(time.time() * 1000)
        # Snapshotting
        self.grafana.create_grafana_urls({'from_ts': from_ts, 'to_ts': to_ts})
        self.grafana.print_dashboard_url(test_name)
        self.grafana.log_snapshot_playbook_cmd(
            from_ts, to_ts, result_dir, test_name)
        self.grafana.run_playbook(from_ts, to_ts, result_dir, test_name)
        # Send Data to elastic
        if self.config['elasticsearch']['enabled']:
            self.send_to_elastic(outputfile, scenario['name'], shaker_uuid)

    def run_shaker(self):
        self.logger.info("Starting Shaker workloads")
        time_stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        self.logger.debug("Time Stamp (Prefix): {}".format(time_stamp))
        scenarios = self.config.get('shaker')['scenarios']
        venv = self.config['shaker']['venv']
        self.shaker_checks()
        if (scenarios is not None and len(scenarios) > 0):
            for scenario in scenarios:
                if scenario['enabled']:
                    self.update_scenarios()
                    self.update_total_scenarios()
                    self.logger.info("Scenario: {}".format(scenario['name']))
                    fname = os.path.join(venv, scenario['file'])
                    self.set_scenario(scenario, fname)
                    self.logger.debug("Set Scenario File: {}".format(
                        fname))
                    result_dir = self.tools.create_results_dir(
                        self.config['browbeat'][
                            'results'], time_stamp, "shaker",
                        scenario['name'])
                    workload = self.__class__.__name__
                    self.workload_logger(result_dir, workload)
                    time_stamp1 = datetime.datetime.utcnow().strftime(
                        "%Y%m%d-%H%M%S")
                    test_name = "{}-browbeat-{}-{}".format(
                        time_stamp1, "shaker", scenario['name'])
                    self.run_scenario(scenario, result_dir, test_name, fname)
                    self.get_stats()
                else:
                    self.logger.info(
                        "Skipping {} as scenario enabled: false".format(
                            scenario['name']))
            self.final_stats(self.scenario_count)
        else:
            self.logger.error(
                "Configuration file contains no shaker scenarios")

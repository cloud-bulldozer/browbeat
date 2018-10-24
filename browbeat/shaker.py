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

import collections
import datetime
import json
import logging
import os
import time
import uuid
import yaml

import elastic
import grafana
from path import get_overcloudrc
from path import get_workload_venv
from path import results_path
import workloadbase
import tools


class Shaker(workloadbase.WorkloadBase):

    def __init__(self, config, result_dir_ts):
        self.logger = logging.getLogger('browbeat.shaker')
        self.overcloudrc = get_overcloudrc()
        self.config = config
        self.result_dir_ts = result_dir_ts
        self.tools = tools.Tools(self.config)
        self.grafana = grafana.Grafana(self.config)
        self.elastic = elastic.Elastic(self.config, self.__class__.__name__.lower())

    def shaker_checks(self):
        cmd = "source {}; source {}; glance image-list | grep -w shaker-image".format(
            get_workload_venv('shaker', True), self.overcloudrc)
        if self.tools.run_cmd(cmd)['stdout'] == "":
            self.logger.error("Shaker Image is not built, try again")
            exit(1)
        else:
            self.logger.info("Shaker image is built, continuing")

    def accommodation_to_dict(self, accommodation):
        accommodation_dict = {}
        for item in accommodation:
            if isinstance(item, dict):
                accommodation_dict.update(item)
            else:
                accommodation_dict[item] = True
        return accommodation_dict

    def accommodation_to_list(self, accommodation):
        accommodation_list = []
        for key, value in accommodation.iteritems():
            if value is True:
                accommodation_list.append(key)
            else:
                temp_dict = {}
                temp_dict[key] = value
                accommodation_list.append(temp_dict)
        return accommodation_list

    # Method to process JSON outputted by Shaker, model data in a format that can be consumed
    # by ElasticSearch and ship the data to ES
    def send_to_elastic(self, outputfile, browbeat_scenario,
                        shaker_uuid, es_ts, es_list, run, test_name, result_dir):
        fname = outputfile
        failure = False
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
                'record': record,
                'browbeat_rerun': run
            }

            result = self.elastic.combine_metadata(shaker_stats)
            index_status = self.elastic.index_result(result, test_name, result_dir, _type='error')
            if index_status is False:
                self.update_index_failures()
                return False
            else:
                return True
        # Dictionary to capture common test data
        shaker_test_meta = {}
        for scenario in data['scenarios'].iterkeys():
            # Populating common test data
            if 'shaker_test_info' not in shaker_test_meta:
                shaker_test_meta['shaker_test_info'] = data[
                    'scenarios'][scenario]
                if "progression" not in shaker_test_meta[
                        'shaker_test_info']['execution']:
                    shaker_test_meta['shaker_test_info'][
                        'execution']['progression'] = "all"
                accommodation = self.accommodation_to_dict(data['scenarios'][scenario][
                    'deployment'].pop('accommodation'))
            if 'deployment' not in shaker_test_meta:
                shaker_test_meta['deployment'] = {}
                shaker_test_meta['deployment']['accommodation'] = {}
                if 'single' in accommodation:
                    shaker_test_meta['deployment'][
                        'accommodation']['distribution'] = 'single'
                elif 'pair' in accommodation:
                    shaker_test_meta['deployment'][
                        'accommodation']['distribution'] = 'pair'
                if 'single_room' in accommodation:
                    shaker_test_meta['deployment'][
                        'accommodation']['placement'] = 'single_room'
                elif 'double_room' in accommodation:
                    shaker_test_meta['deployment'][
                        'accommodation']['placement'] = 'double_room'
                if 'density' in accommodation:
                    shaker_test_meta['deployment']['accommodation'][
                        'density'] = accommodation['density']
                if 'compute_nodes' in accommodation:
                    shaker_test_meta['deployment']['accommodation'][
                        'compute_nodes'] = accommodation['compute_nodes']
                shaker_test_meta['deployment']['template'] = data[
                    'scenarios'][scenario]['deployment']['template']
        # Iterating through each record to get result values
        for record in data['records'].iterkeys():
            if data['records'][record]['status'] == "ok" and data[
                    'records'][record]['executor'] != "shell":
                if 'stdout' in data['records'][record]:
                    del data['records'][record]['stdout']
                metadata = data['records'][record].pop('meta')
                samples = data['records'][record].pop('samples')
                # Ordered Dictionary to capture result types and metrics
                outputs = collections.OrderedDict()
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
                        # list of samples for each test type(tcp download/ping_icmp) for each
                        # record afterrecord after flattening out data
                        shaker_stats = {
                            'record': data['records'][record],
                            'browbeat_rerun': run,
                            'shaker_test_info': shaker_test_meta['shaker_test_info'],
                            'timestamp': elastic_timestamp,
                            'accommodation': shaker_test_meta['deployment']['accommodation'],
                            'template': shaker_test_meta['deployment']['template'],
                            'result': result,
                            'browbeat_scenario': browbeat_scenario,
                            'grafana_url': [
                                self.grafana.grafana_urls()],
                            'shaker_uuid': str(shaker_uuid)}
                        identifier = elastic_timestamp + '-' + record + '-' + result['result_type']
                        # Ship Data to ES when record status is ok
                        if result['value'] is None:
                            self.logger.debug("Ignoring sending null values to ES")
                        else:
                            result = self.elastic.combine_metadata(shaker_stats)
                            index_status = self.elastic.index_result(result, test_name, result_dir,
                                                                     identifier)
                            if index_status is False:
                                failure = True
            else:
                # If the status of the record is not OK or if the type of
                # executor is shell, ship minimal
                # shaker_stats dictionary to ES
                shaker_stats = {
                    'record': data['records'][record],
                    'browbeat_rerun': run,
                    'shaker_test_info': shaker_test_meta['shaker_test_info'],
                    'timestamp': str(es_ts).replace(" ", "T"),
                    'accommodation': shaker_test_meta['deployment']['accommodation'],
                    'template': shaker_test_meta['deployment']['template'],
                    'browbeat_scenario': browbeat_scenario,
                    'grafana_url': [self.grafana.grafana_urls()],
                    'shaker_uuid': str(shaker_uuid)}
                identifier = record
                result = self.elastic.combine_metadata(shaker_stats)
                index_status = self.elastic.index_result(result, test_name, result_dir, identifier,
                                                         _type='error')
                if index_status is False:
                    failure = True
        if failure:
            return False
        else:
            return True

    def set_scenario(self, scenario, fname, default_time):
        stream = open(fname, 'r')
        data = yaml.safe_load(stream)
        stream.close()
        default_density = 1
        default_compute = 1
        default_progression = "linear"
        accommodation = self.accommodation_to_dict(data['deployment']['accommodation'])
        if 'placement' in scenario and any(k in accommodation for k in ('single_room',
                                                                        'double_room')):
            if 'single_room' in accommodation and scenario['placement'] == 'double_room':
                accommodation.pop('single_room', None)
                accommodation['double_room'] = True
            elif 'double_room' in accommodation and scenario['placement'] == 'single_room':
                accommodation['single_room'] = True
                accommodation.pop('double_room', None)
        else:
            accommodation['double_room'] = True
            accommodation.pop('single_room', None)
        if 'density' in scenario and 'density' in accommodation:
            accommodation['density'] = scenario['density']
        elif 'density' in accommodation:
            accommodation['density'] = default_density
        if "compute" in scenario and 'compute_nodes' in accommodation:
            accommodation['compute_nodes'] = scenario['compute']
        elif 'compute_nodes' in accommodation:
            accommodation['compute_nodes'] = default_compute
        accommodation = self.accommodation_to_list(accommodation)
        self.logger.debug("Using accommodation {}".format(accommodation))
        data['deployment']['accommodation'] = accommodation
        if 'progression' in scenario and 'progression' in data['execution']:
            if scenario['progression'] is None:
                data['execution'].pop('progression', None)
            else:
                data['execution']['progression'] = scenario['progression']
        elif 'progression' in data['execution']:
            data['execution']['progression'] = default_progression
        if 'time' in scenario:
            for test in data['execution']['tests']:
                test['time'] = scenario['time']
        else:
            for test in data['execution']['tests']:
                test['time'] = default_time
        self.logger.debug("Execution time of each test set to {}".format(test['time']))
        with open(fname, 'w') as yaml_file:
            yaml_file.write(yaml.safe_dump(data, default_flow_style=False))

    def get_uuidlist(self, data):
        uuidlist = []
        for key in data['records'].iterkeys():
            uuidlist.append(key)
        return uuidlist

    def result_check(self, result_dir, test_name, scenario,
                     to_time, from_time, index_status="disabled"):
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
            self.logger.error("Cannot open outputfile, possible stack creation"
                              "failure for test: {}". format(scenario['name']))
            self.error_update(result_dir, test_name, scenario, to_time,
                              from_time, new_test_name, workload, index_status)
            return
        uuidlist = self.get_uuidlist(data)
        for id in uuidlist:
            if data['records'][id]['status'] != "ok":
                error = True
        if error:
            self.error_update(result_dir, test_name, scenario,
                              to_time, from_time, new_test_name,
                              workload, index_status)
        else:
            self.success_update(result_dir, test_name, scenario, to_time,
                                from_time, new_test_name, workload, index_status)

    def error_update(self, result_dir, test_name, scenario, to_time, from_time,
                     new_test_name, workload, index_status):
        self.logger.error("Failed Test: {}".format(scenario['name']))
        self.logger.error("saved log to: {}.log".format(os.path.join(result_dir,
                                                                     test_name)))
        self.update_total_fail_tests()
        self.get_time_dict(to_time, from_time, scenario['name'],
                           new_test_name, workload, "fail", index_status)

    def success_update(self, result_dir, test_name, scenario, to_time,
                       from_time, new_test_name, workload, index_status):
        self.logger.info("Completed Test: {}".format(scenario['name']))
        self.logger.info("Saved report to: {}.html".
                         format(os.path.join(result_dir, test_name)))
        self.logger.info("saved log to: {}.log".format(os.path.join(result_dir,
                                                                    test_name)))
        self.update_total_pass_tests()
        self.get_time_dict(to_time, from_time, scenario['name'],
                           new_test_name, workload, "pass", index_status)

    def run_scenario(self, scenario, result_dir, test_name, filename,
                     shaker_uuid, es_ts, es_list, run):
        server_endpoint = self.config['shaker']['server']
        port_no = self.config['shaker']['port']
        flavor = self.config['shaker']['flavor']
        venv = get_workload_venv('shaker', True)
        shaker_region = self.config['shaker']['shaker_region']
        timeout = self.config['shaker']['join_timeout']
        self.logger.info(
            "The uuid for this shaker scenario is {}".format(shaker_uuid))
        cmd_env = (
            "source {0}; source {1}").format(venv, self.overcloudrc)
        if 'external' in filename and 'external_host' in self.config['shaker']:
            external_host = self.config['shaker']['external_host']
            cmd_shaker = (
                'shaker --server-endpoint {0}:{1} --flavor-name {2} --scenario {3}'
                ' --os-region-name {7} --agent-join-timeout {6}'
                ' --report {4}/{5}.html --output {4}/{5}.json'
                ' --book {4}/{5} --matrix "{{host: {8}}}" --debug'
                ' > {4}/{5}.log 2>&1').format(server_endpoint,
                                              port_no, flavor, filename, result_dir,
                                              test_name, timeout, shaker_region,
                                              external_host)
        else:
            cmd_shaker = (
                'shaker --server-endpoint {0}:{1} --flavor-name {2} --scenario {3}'
                ' --os-region-name {7} --agent-join-timeout {6}'
                ' --report {4}/{5}.html --output {4}/{5}.json'
                ' --book {4}/{5} --debug'
                ' > {4}/{5}.log 2>&1').format(server_endpoint, port_no, flavor,
                                              filename, result_dir, test_name,
                                              timeout, shaker_region)
        cmd = ("{}; {}").format(cmd_env, cmd_shaker)
        from_ts = int(time.time() * 1000)
        if 'sleep_before' in self.config['shaker']:
            time.sleep(self.config['shaker']['sleep_before'])
        from_time = time.time()
        self.tools.run_cmd(cmd)
        to_time = time.time()
        self.update_total_tests()
        outputfile = os.path.join(result_dir, test_name + "." + "json")
        if 'sleep_after' in self.config['shaker']:
            time.sleep(self.config['shaker']['sleep_after'])
        to_ts = int(time.time() * 1000)
        # Snapshotting
        self.grafana.create_grafana_urls({'from_ts': from_ts, 'to_ts': to_ts})
        self.grafana.print_dashboard_url(test_name)
        # Send Data to elastic
        if self.config['elasticsearch']['enabled']:
            index_status = self.send_to_elastic(outputfile, scenario['name'], shaker_uuid,
                                                es_ts, es_list, run, test_name, result_dir)
            self.result_check(result_dir, test_name, scenario, to_time, from_time, index_status)
        else:
            self.result_check(result_dir, test_name, scenario, to_time, from_time)

    def run_workload(self, workload, run_iteration):
        self.logger.info("Starting Shaker workloads")
        time_stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        self.logger.debug("Time Stamp (Prefix): {}".format(time_stamp))

        venv = get_workload_venv('shaker', False)
        self.shaker_checks()

        self.update_total_scenarios()
        shaker_uuid = uuid.uuid4()
        es_ts = datetime.datetime.utcnow()
        es_list = []
        # Default test time to 60
        test_time = workload.get("time", 60)
        for interval in range(0, test_time + 9):
            es_list.append(
                datetime.datetime.utcnow() + datetime.timedelta(0, interval))

        rerun_range = range(self.config["browbeat"]["rerun"])
        if self.config["browbeat"]["rerun_type"] == "complete":
            # Compelete rerun type means force
            rerun_range = range(run_iteration, run_iteration + 1)

        for run in rerun_range:
            self.logger.info("Scenario: {}".format(workload['name']))
            self.logger.info("Run: {}".format(run))
            fname = os.path.join(venv, workload['file'])
            self.set_scenario(workload, fname, 60)
            self.logger.debug("Set Scenario File: {}".format(fname))
            result_dir = self.tools.create_results_dir(
                results_path, self.result_dir_ts, "shaker",
                workload['name'] + "-" + str(run))
            self.workload_logger(self.__class__.__name__)
            time_stamp1 = datetime.datetime.now().strftime(
                "%Y%m%d-%H%M%S")
            test_name = "{}-browbeat-{}-{}-{}".format(
                time_stamp1, "shaker", workload['name'], run)
            self.run_scenario(
                workload, result_dir, test_name, fname, shaker_uuid,
                es_ts, es_list, run)

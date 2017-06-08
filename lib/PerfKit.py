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

import ast
import Connmon
import datetime
import Elastic
import glob
import Grafana
import logging
import os
import shutil
import subprocess
import time
import Tools
import WorkloadBase


class PerfKit(WorkloadBase.WorkloadBase):

    def __init__(self, config):
        self.logger = logging.getLogger('browbeat.PerfKit')
        self.config = config
        self.error_count = 0
        self.tools = Tools.Tools(self.config)
        self.connmon = Connmon.Connmon(self.config)
        self.grafana = Grafana.Grafana(self.config)
        self.elastic = Elastic.Elastic(self.config, self.__class__.__name__.lower())
        self.test_count = 0
        self.scenario_count = 0
        self.pass_count = 0

    def _log_details(self):
        self.logger.info(
            "Current number of Perkit scenarios executed: {}".format(self.scenario_count))
        self.logger.info(
            "Current number of Perfkit test(s) executed: {}".format(self.test_count))
        self.logger.info(
            "Current number of Perfkit test(s) succeeded: {}".format(self.pass_count))
        self.logger.info(
            "Current number of Perfkit test failures: {}".format(self.error_count))

    def string_to_dict(self, string):
        """Function for converting "|" quoted hash data into python dictionary."""
        dict_data = {}
        split_data = string.split('|,|')
        split_data[0] = split_data[0][1:]
        split_data[-1] = split_data[-1][:-1]
        for item in split_data:
            split_item = item.replace('.', '_').split(':', 1)
            dict_data[split_item[0]] = ast.literal_eval("'" + split_item[1] + "'")
        return dict_data

    def update_tests(self):
        self.test_count += 1

    def update_pass_tests(self):
        self.pass_count += 1

    def update_fail_tests(self):
        self.error_count += 1

    def update_scenarios(self):
        self.scenario_count += 1

    def get_error_details(self, result_dir):
        error_details = []
        with open('{}/pkb.stderr.log'.format(result_dir)) as perfkit_stderr:
            for line in perfkit_stderr:
                if 'ERROR' in line or 'Error' in line or 'Exception' in line:
                    error_details.append(line)
        return error_details

    def index_results(self, sucessful_run, result_dir, test_name, browbeat_rerun, benchmark_config):
        es_ts = datetime.datetime.utcnow()
        index_success = True
        if sucessful_run:
            # PerfKit json is newline delimited and thus each newline json needs to be indexed
            with open('{}/perfkitbenchmarker_results.json'.format(result_dir)) \
                    as perfkit_results_json:
                for result_count, json_result in enumerate(perfkit_results_json):
                    complete_result_json = {'browbeat_scenario': benchmark_config}
                    complete_result_json['results'] = {'unit':{}, 'value': {}}
                    single_result = self.elastic.load_json(json_result.strip())
                    complete_result_json['browbeat_rerun'] = browbeat_rerun
                    complete_result_json['timestamp'] = str(es_ts).replace(" ", "T")
                    complete_result_json['grafana_url'] = self.grafana.grafana_urls()
                    complete_result_json['perfkit_setup'] = \
                        self.string_to_dict(single_result['labels'])
                    result_metric = single_result['metric'].lower().replace(' ', '_'). \
                        replace('.', '_')
                    complete_result_json['results']['value'][result_metric] = single_result['value']
                    complete_result_json['results']['unit'][result_metric] = single_result['unit']
                    result = self.elastic.combine_metadata(complete_result_json)
                    if not self.elastic.index_result(result, test_name, result_dir,
                                                     str(result_count), 'result'):
                        index_success = False
                        self.update_index_failures()
        else:
            complete_result_json = {'browbeat_scenario': benchmark_config}
            complete_result_json['perfkit_errors'] = self.get_error_details(result_dir)
            complete_result_json['browbeat_rerun'] = browbeat_rerun
            complete_result_json['timestamp'] = str(es_ts).replace(" ", "T")
            complete_result_json['grafana_url'] = self.grafana.grafana_urls()
            result = self.elastic.combine_metadata(complete_result_json)
            index_success = self.elastic.index_result(result, test_name, result_dir, _type='error')
        return index_success

    def run_benchmark(self, benchmark_config, result_dir, test_name, cloud_type="OpenStack"):
        self.logger.debug("--------------------------------")
        self.logger.debug("Benchmark_config: {}".format(benchmark_config))
        self.logger.debug("result_dir: {}".format(result_dir))
        self.logger.debug("test_name: {}".format(test_name))
        self.logger.debug("--------------------------------")

        # Build command to run
        if 'enabled' in benchmark_config:
            del benchmark_config['enabled']
        cmd = ("source /home/stack/overcloudrc; source {0}; "
               "/home/stack/perfkit-venv/PerfKitBenchmarker/pkb.py "
               "--cloud={1} --run_uri=browbeat".format(self.config['perfkit']['venv'], cloud_type))
        for parameter, value in benchmark_config.iteritems():
            if not parameter == 'name':
                self.logger.debug(
                    "Parameter: {}, Value: {}".format(parameter, value))
                cmd += " --{}={}".format(parameter, value)

        # Remove any old results
        if os.path.exists("/tmp/perfkitbenchmarker/runs/browbeat"):
            shutil.rmtree("/tmp/perfkitbenchmarker/runs/browbeat")

        if self.config['connmon']['enabled']:
            self.connmon.start_connmon()

        self.logger.info("Running Perfkit Command: {}".format(cmd))
        stdout_file = open("{}/pkb.stdout.log".format(result_dir), 'w')
        stderr_file = open("{}/pkb.stderr.log".format(result_dir), 'w')
        from_ts = time.time()
        if 'sleep_before' in self.config['perfkit']:
            time.sleep(self.config['perfkit']['sleep_before'])
        process = subprocess.Popen(
            cmd, shell=True, stdout=stdout_file, stderr=stderr_file)
        process.communicate()
        if 'sleep_after' in self.config['perfkit']:
            time.sleep(self.config['perfkit']['sleep_after'])
        to_ts = time.time()

        # Stop connmon at end of perfkit task
        if self.config['connmon']['enabled']:
            self.connmon.stop_connmon()
            try:
                self.connmon.move_connmon_results(result_dir, test_name)
                self.connmon.connmon_graphs(result_dir, test_name)
            except Exception:
                self.logger.error(
                    "Connmon Result data missing, Connmon never started")

        # Determine success
        success = False
        try:
            with open("{}/pkb.stderr.log".format(result_dir), 'r') as stderr:
                if any('SUCCEEDED' in line for line in stderr):
                    self.logger.info("Benchmark completed.")
                    success = True
                else:
                    self.logger.error("Benchmark failed.")
        except IOError:
            self.logger.error(
                "File missing: {}/pkb.stderr.log".format(result_dir))

        # Copy all results
        for perfkit_file in glob.glob("/tmp/perfkitbenchmarker/runs/browbeat/*"):
            shutil.move(perfkit_file, result_dir)
        if os.path.exists("/tmp/perfkitbenchmarker/runs/browbeat"):
            shutil.rmtree("/tmp/perfkitbenchmarker/runs/browbeat")

        # Grafana integration
        self.grafana.create_grafana_urls(
            {'from_ts': int(from_ts * 1000),
             'to_ts': int(to_ts * 1000)})
        self.grafana.print_dashboard_url(test_name)
        self.grafana.log_snapshot_playbook_cmd(
            from_ts, to_ts, result_dir, test_name)
        self.grafana.run_playbook(from_ts, to_ts, result_dir, test_name)

        return success, to_ts, from_ts

    def start_workloads(self):
        self.logger.info("Starting PerfKitBenchmarker Workloads.")
        time_stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        self.logger.debug("Time Stamp (Prefix): {}".format(time_stamp))
        benchmarks = self.config.get('perfkit')['benchmarks']
        if (benchmarks is not None and len(benchmarks) > 0):
            for benchmark in benchmarks:
                if benchmark['enabled']:
                    self.logger.info("Benchmark: {}".format(benchmark['name']))
                    self.update_scenarios()
                    self.update_total_scenarios()
                    # Add default parameters as necessary
                    for default_item, value in self.config['perfkit']['default'].iteritems():
                        if default_item not in benchmark:
                            benchmark[default_item] = value
                    for run in range(self.config['browbeat']['rerun']):
                        self.update_tests()
                        self.update_total_tests()
                        result_dir = self.tools.create_results_dir(
                            self.config['browbeat']['results'], time_stamp, benchmark['name'],
                            str(run))
                        test_name = "{}-{}-{}".format(time_stamp, benchmark['name'], run)
                        workload = self.__class__.__name__
                        self.workload_logger(result_dir, workload)
                        success, to_ts, from_ts = self.run_benchmark(benchmark, result_dir,
                                                                     test_name)
                        index_success = 'disabled'
                        if self.config['elasticsearch']['enabled']:
                            index_success = self.index_results(success, result_dir, test_name, run,
                                                               benchmark)
                        new_test_name = test_name.split('-')
                        new_test_name = new_test_name[2:]
                        new_test_name = '-'.join(new_test_name)
                        if success:
                            self.update_pass_tests()
                            self.update_total_pass_tests()
                            self.get_time_dict(to_ts, from_ts, benchmark['benchmarks'],
                                               new_test_name, self.__class__.__name__, "pass",
                                               index_success)
                        else:
                            self.update_fail_tests()
                            self.update_total_fail_tests()
                            self.get_time_dict(to_ts, from_ts, benchmark['benchmarks'],
                                               new_test_name, self.__class__.__name__, "fail",
                                               index_success)
                        self._log_details()
                else:
                    self.logger.info(
                        "Skipping {} benchmark, enabled: false".format(benchmark['name']))
        else:
            self.logger.error("Config file contains no perfkit benchmarks.")

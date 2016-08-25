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

import Connmon
import datetime
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

    def update_tests(self):
        self.test_count += 1

    def update_pass_tests(self):
        self.pass_count += 1

    def update_fail_tests(self):
        self.error_count += 1

    def update_scenarios(self):
        self.scenario_count += 1

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
        # Add default parameters as necessary
        for default_item, value in self.config['perfkit']['default'].iteritems():
            if default_item not in benchmark_config:
                benchmark_config[default_item] = value
        for parameter, value in benchmark_config.iteritems():
            if not parameter == 'name':
                self.logger.debug(
                    "Parameter: {}, Value: {}".format(parameter, value))
                cmd += " --{}={}".format(parameter, value)

        # Remove any old results
        if os.path.exists("/tmp/perfkitbenchmarker/run_browbeat"):
            shutil.rmtree("/tmp/perfkitbenchmarker/run_browbeat")

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

        workload = self.__class__.__name__
        new_test_name = test_name.split('-')
        new_test_name = new_test_name[2:]
        new_test_name = '-'.join(new_test_name)
        # Determine success
        try:
            with open("{}/pkb.stderr.log".format(result_dir), 'r') as stderr:
                if any('SUCCEEDED' in line for line in stderr):
                    self.logger.info("Benchmark completed.")
                    self.update_pass_tests()
                    self.update_total_pass_tests()
                    self.get_time_dict(
                        to_ts, from_ts, benchmark_config[
                            'benchmarks'], new_test_name,
                        workload, "pass")
                else:
                    self.logger.error("Benchmark failed.")
                    self.update_fail_tests()
                    self.update_total_fail_tests()
                    self.get_time_dict(
                        to_ts, from_ts, benchmark_config[
                            'benchmarks'], new_test_name,
                        workload, "fail")
        except IOError:
            self.logger.error(
                "File missing: {}/pkb.stderr.log".format(result_dir))

        # Copy all results
        for perfkit_file in glob.glob("/tmp/perfkitbenchmarker/run_browbeat/*"):
            shutil.move(perfkit_file, result_dir)
        if os.path.exists("/tmp/perfkitbenchmarker/run_browbeat"):
            shutil.rmtree("/tmp/perfkitbenchmarker/run_browbeat")

        # Grafana integration
        self.grafana.create_grafana_urls(
            {'from_ts': int(from_ts * 1000),
             'to_ts': int(to_ts * 1000)})
        self.grafana.print_dashboard_url(test_name)
        self.grafana.log_snapshot_playbook_cmd(
            from_ts, to_ts, result_dir, test_name)
        self.grafana.run_playbook(from_ts, to_ts, result_dir, test_name)

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
                    for run in range(self.config['browbeat']['rerun']):
                        self.update_tests()
                        self.update_total_tests()
                        result_dir = self.tools.create_results_dir(
                            self.config['browbeat']['results'], time_stamp, benchmark['name'], run)
                        test_name = "{}-{}-{}".format(time_stamp,
                                                      benchmark['name'], run)
                        workload = self.__class__.__name__
                        self.workload_logger(result_dir, workload)
                        self.run_benchmark(benchmark, result_dir, test_name)
                        self._log_details()
                else:
                    self.logger.info(
                        "Skipping {} benchmark, enabled: false".format(benchmark['name']))
        else:
            self.logger.error("Config file contains no perfkit benchmarks.")

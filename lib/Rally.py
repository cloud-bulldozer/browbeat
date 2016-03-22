from Connmon import Connmon
from Tools import Tools
from collections import OrderedDict
from Grafana import Grafana
from WorkloadBase import WorkloadBase
import datetime
import glob
import logging
import os
import shutil
import subprocess
import time

class Rally(WorkloadBase):

    def __init__(self, config, hosts=None):
        self.logger = logging.getLogger('browbeat.Rally')
        self.config = config
        self.tools = Tools(self.config)
        self.connmon = Connmon(self.config)
        self.grafana = Grafana(self.config)
        self.error_count = 0
        self.pass_count = 0
        self.test_count = 0
        self.scenario_count = 0

    def run_scenario(self, task_file, scenario_args, result_dir, test_name, benchmark):
        self.logger.debug("--------------------------------")
        self.logger.debug("task_file: {}".format(task_file))
        self.logger.debug("scenario_args: {}".format(scenario_args))
        self.logger.debug("result_dir: {}".format(result_dir))
        self.logger.debug("test_name: {}".format(test_name))
        self.logger.debug("--------------------------------")

        from_ts = int(time.time() * 1000)
        if 'sleep_before' in self.config['rally']:
            time.sleep(self.config['rally']['sleep_before'])
        task_args = str(scenario_args).replace("'", "\"")
        plugins = []
        if "plugins" in self.config['rally']:
            if len(self.config['rally']['plugins']) > 0:
                for plugin in self.config['rally']['plugins']:
                    for name in plugin:
                        plugins.append(plugin[name])
        plugin_string = ""
        if len(plugins) > 0:
            plugin_string = "--plugin-paths {}".format(",".join(plugins))
        cmd = "source {}; ".format(self.config['rally']['venv'])
        cmd += "rally {} task start {} --task-args \'{}\' 2>&1 | tee {}.log".format(
            plugin_string, task_file,task_args, test_name)
        from_time = time.time()
        self.tools.run_cmd(cmd)
        to_time = time.time()
        if 'sleep_after' in self.config['rally']:
            time.sleep(self.config['rally']['sleep_after'])
        to_ts = int(time.time() * 1000)
        return (from_time, to_time)
        self.grafana.print_dashboard_url(from_ts, to_ts, test_name)
        self.grafana.log_snapshot_playbook_cmd(
            from_ts, to_ts, result_dir, test_name)
        self.grafana.run_playbook(from_ts, to_ts, result_dir, test_name)

    def update_tests(self):
        self.test_count += 1

    def update_pass_tests(self):
        self.pass_count += 1

    def update_fail_tests(self):
        self.error_count += 1

    def update_scenarios(self):
        self.scenario_count += 1

    def get_task_id(self, test_name):
        cmd = "grep \"rally task results\" {}.log | awk '{{print $4}}'".format(
            test_name)
        return self.tools.run_cmd(cmd)

    def _get_details(self):
        self.logger.info(
            "Current number of Rally scenarios executed:{}".format(
                self.scenario_count))
        self.logger.info("Current number of Rally tests executed:{}".format(self.test_count))
        self.logger.info("Current number of Rally tests passed:{}".format(self.pass_count))
        self.logger.info("Current number of Rally test failures:{}".format(self.error_count))

    def gen_scenario_html(self, task_ids, test_name):
        all_task_ids = ' '.join(task_ids)
        cmd = "source {}; ".format(self.config['rally']['venv'])
        cmd += "rally task report --task {} --out {}.html".format(
            all_task_ids, test_name)
        return self.tools.run_cmd(cmd)

    def gen_scenario_json(self, task_id, test_name):
        cmd = "source {}; ".format(self.config['rally']['venv'])
        cmd += "rally task results {} > {}.json".format(task_id, test_name)
        return self.tools.run_cmd(cmd)

    def start_workloads(self):
        """Iterates through all rally scenarios in browbeat yaml config file"""
        results = OrderedDict()
        self.logger.info("Starting Rally workloads")
        time_stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.logger.debug("Time Stamp (Prefix): {}".format(time_stamp))
        benchmarks = self.config.get('rally')['benchmarks']
        if len(benchmarks) > 0:
            for benchmark in benchmarks:
                if benchmark['enabled']:
                    self.logger.info("Benchmark: {}".format(benchmark['name']))
                    scenarios = benchmark['scenarios']
                    def_concurrencies = benchmark['concurrency']
                    def_times = benchmark['times']
                    self.logger.debug(
                        "Default Concurrencies: {}".format(def_concurrencies))
                    self.logger.debug("Default Times: {}".format(def_times))
                    for scenario in scenarios:
                        if scenario['enabled']:
                            self.update_scenarios()
                            self.update_total_scenarios()
                            scenario_name = scenario['name']
                            scenario_file = scenario['file']
                            self.logger.info(
                                "Running Scenario: {}".format(scenario_name))
                            self.logger.debug(
                                "Scenario File: {}".format(scenario_file))

                            del scenario['enabled']
                            del scenario['file']
                            del scenario['name']
                            if len(scenario) > 0:
                                self.logger.debug(
                                    "Overriding Scenario Args: {}".format(scenario))

                            result_dir = self.tools.create_results_dir(
                                self.config['browbeat'][
                                    'results'], time_stamp, benchmark['name'],
                                scenario_name)
                            self.logger.debug("Created result directory: {}".format(result_dir))
                            workload = self.__class__.__name__
                            self.workload_logger(result_dir, workload)

                            # Override concurrency/times
                            if 'concurrency' in scenario:
                                concurrencies = scenario['concurrency']
                                del scenario['concurrency']
                            else:
                                concurrencies = def_concurrencies
                            if 'times' not in scenario:
                                scenario['times'] = def_times

                            for concurrency in concurrencies:
                                scenario['concurrency'] = concurrency
                                for run in range(self.config['browbeat']['rerun']):
                                    if run not in results:
                                        results[run] = []
                                    self.update_tests()
                                    self.update_total_tests()
                                    test_name = "{}-browbeat-{}-{}-iteration-{}".format(
                                        time_stamp, scenario_name, concurrency, run)

                                    if not result_dir:
                                        self.logger.error(
                                            "Failed to create result directory")
                                        exit(1)

                                    # Start connmon before rally
                                    if self.config['connmon']['enabled']:
                                        self.connmon.start_connmon()

                                    from_time,to_time = self.run_scenario(
                                        scenario_file, scenario, result_dir, test_name,
                                        benchmark['name'])

                                    # Stop connmon at end of rally task
                                    if self.config['connmon']['enabled']:
                                        self.connmon.stop_connmon()
                                        try:
                                            self.connmon.move_connmon_results(
                                                result_dir, test_name)
                                        except:
                                            self.logger.error(
                                                "Connmon Result data missing, \
                                                Connmon never started")
                                            return False
                                        self.connmon.connmon_graphs(result_dir, test_name)
                                    new_test_name = test_name.split('-')
                                    new_test_name = new_test_name[3:]
                                    new_test_name = "-".join(new_test_name)

                                    # Find task id (if task succeeded in
                                    # running)
                                    task_id = self.get_task_id(test_name)
                                    if task_id:
                                        self.logger.info(
                                            "Generating Rally HTML for task_id : {}".
                                            format(task_id))
                                        self.gen_scenario_html(
                                            [task_id], test_name)
                                        self.gen_scenario_json(
                                            task_id, test_name)
                                        results[run].append(task_id)
                                        self.update_pass_tests()
                                        self.update_total_pass_tests()
                                        self.get_time_dict(
                                            to_time, from_time, benchmark['name'], new_test_name,
                                            workload, "pass")

                                    else:
                                        self.logger.error("Cannot find task_id")
                                        self.update_fail_tests()
                                        self.update_total_fail_tests()
                                        self.get_time_dict(
                                            to_time, from_time, benchmark['name'], new_test_name,
                                            workload, "fail")

                                    for data in glob.glob("./{}*".format(test_name)):
                                        shutil.move(data, result_dir)

                                    self._get_details()

                        else:
                            self.logger.info(
                                "Skipping {} scenario enabled: false".format(scenario['name']))
                else:
                    self.logger.info(
                        "Skipping {} benchmarks enabled: false".format(benchmark['name']))
            self.logger.debug("Creating Combined Rally Reports")
            for run in results:
                combined_html_name = 'all-rally-run-{}'.format(run)
                self.gen_scenario_html(results[run], combined_html_name)
                if os.path.isfile('{}.html'.format(combined_html_name)):
                    shutil.move('{}.html'.format(combined_html_name),
                                '{}/{}'.format(self.config['browbeat']['results'], time_stamp))
        else:
            self.logger.error("Config file contains no rally benchmarks.")

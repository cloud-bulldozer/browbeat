from Connmon import Connmon
from Tools import Tools
import glob
import logging
import datetime
import os
import shutil
import subprocess
import time


class PerfKit:
    def __init__(self, config):
        self.logger = logging.getLogger('browbeat.PerfKit')
        self.config = config
        self.error_count = 0
        self.tools = Tools(self.config)
        self.connmon = Connmon(self.config)
        self.test_count = 0
        self.scenario_count = 0

    def _log_details(self):
        self.logger.info("Current number of scenarios executed: {}".format(self.scenario_count))
        self.logger.info("Current number of test(s) executed: {}".format(self.test_count))
        self.logger.info("Current number of test failures: {}".format(self.error_count))

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
                self.logger.debug("Parameter: {}, Value: {}".format(parameter, value))
                cmd += " --{}={}".format(parameter, value)

        # Remove any old results
        if os.path.exists("/tmp/perfkitbenchmarker/run_browbeat"):
            shutil.rmtree("/tmp/perfkitbenchmarker/run_browbeat")

        if self.config['browbeat']['connmon']:
            self.connmon.start_connmon()

        # Run PerfKit
        from_ts = int(time.time() * 1000)
        if 'sleep_before' in self.config['perfkit']:
            time.sleep(self.config['perfkit']['sleep_before'])
        self.logger.info("Running Perfkit Command: {}".format(cmd))
        stdout_file = open("{}/pkb.stdout.log".format(result_dir), 'w')
        stderr_file = open("{}/pkb.stderr.log".format(result_dir), 'w')
        process = subprocess.Popen(cmd, shell=True, stdout=stdout_file, stderr=stderr_file)
        process.communicate()
        if 'sleep_after' in self.config['perfkit']:
            time.sleep(self.config['perfkit']['sleep_after'])
        to_ts = int(time.time() * 1000)

        # Stop connmon at end of perfkit task
        if self.config['browbeat']['connmon']:
            self.connmon.stop_connmon()
            try:
                self.connmon.move_connmon_results(result_dir, test_name)
                self.connmon.connmon_graphs(result_dir, test_name)
            except:
                self.logger.error("Connmon Result data missing, Connmon never started")

        # Determine success
        try:
            with open("{}/pkb.stderr.log".format(result_dir), 'r') as stderr:
                if any('SUCCEEDED' in line for line in stderr):
                    self.logger.info("Benchmark completed.")
                else:
                    self.logger.error("Benchmark failed.")
                    self.error_count += 1
        except IOError:
            self.logger.error("File missing: {}/pkb.stderr.log".format(result_dir))

        # Copy all results
        for perfkit_file in glob.glob("/tmp/perfkitbenchmarker/run_browbeat/*"):
            shutil.move(perfkit_file, result_dir)
        if os.path.exists("/tmp/perfkitbenchmarker/run_browbeat"):
            shutil.rmtree("/tmp/perfkitbenchmarker/run_browbeat")

        # Grafana integration
        if 'grafana' in self.config and self.config['grafana']['enabled']:
            grafana_ip = self.config['grafana']['grafana_ip']
            grafana_port = self.config['grafana']['grafana_port']
            url = 'http://{}:{}/dashboard/db/'.format(grafana_ip, grafana_port)
            cloud_name = self.config['grafana']['cloud_name']
            for dashboard in self.config['grafana']['dashboards']:
                full_url = '{}{}?from={}&to={}&var-Cloud={}'.format(url, dashboard, from_ts, to_ts,
                    cloud_name)
                self.logger.info('{} - Grafana URL: {}'.format(test_name, full_url))
            if self.config['grafana']['snapshot']['enabled']:
                hosts_file = self.config['ansible']['hosts']
                playbook = self.config['ansible']['grafana_snapshot']
                extra_vars = 'grafana_ip={} '.format(grafana_ip)
                extra_vars += 'grafana_port={} '.format(grafana_port)
                extra_vars += 'grafana_api_key={} '.format(self.config['grafana']['snapshot']['grafana_api_key'])
                extra_vars += 'from={} '.format(from_ts)
                extra_vars += 'to={} '.format(to_ts)
                extra_vars += 'results_dir={}/{} '.format(result_dir, test_name)
                extra_vars += 'var_cloud={} '.format(cloud_name)
                if self.config['grafana']['snapshot']['snapshot_compute']:
                    extra_vars += 'snapshot_compute=true '
                snapshot_cmd = 'ansible-playbook -i {} {} -e "{}"'.format(hosts_file, playbook,
                    extra_vars)
                subprocess_cmd = ['ansible-playbook', '-i', hosts_file, playbook, '-e',
                    '{}'.format(extra_vars)]
                self.logger.info('Snapshot command: {}'.format(snapshot_cmd))
                snapshot_log = open('{}/snapshot.log'.format(result_dir), 'a+')
                subprocess.Popen(subprocess_cmd, stdout=snapshot_log, stderr=subprocess.STDOUT)

    def start_workloads(self):
        self.logger.info("Starting PerfKitBenchmarker Workloads.")
        time_stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.logger.debug("Time Stamp (Prefix): {}".format(time_stamp))
        benchmarks = self.config.get('perfkit')['benchmarks']
        if len(benchmarks) > 0:
            for benchmark in benchmarks:
                if benchmark['enabled']:
                    self.logger.info("Benchmark: {}".format(benchmark['name']))
                    self.scenario_count += 1
                    for run in range(self.config['browbeat']['rerun']):
                        self.test_count += 1
                        result_dir = self.tools.create_results_dir(
                            self.config['browbeat']['results'], time_stamp, benchmark['name'], run)
                        test_name = "{}-{}-{}".format(time_stamp, benchmark['name'], run)
                        self.run_benchmark(benchmark, result_dir, test_name)
                        self._log_details()
                else:
                    self.logger.info("Skipping {} benchmark, enabled: false".format(benchmark['name']))
        else:
            self.logger.error("Config file contains no perfkit benchmarks.")

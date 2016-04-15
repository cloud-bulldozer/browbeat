from Tools import Tools
from Grafana import Grafana
import yaml
import logging
import datetime
import os
import json
import time


class Shaker:

    def __init__(self, config):
        self.logger = logging.getLogger('browbeat.Shaker')
        self.config = config
        self.tools = Tools(self.config)
        self.grafana = Grafana(self.config)
        self.fail_scenarios = 0
        self.pass_scenarios = 0
        self.scenarios_count = 0

    def shaker_checks(self):
        cmd = "source /home/stack/overcloudrc; glance image-list | grep -w shaker-image"
        if self.tools.run_cmd(cmd) == "":
            self.logger.error("Shaker Image is not built, try again")
            exit(1)
        else:
            self.logger.info("Shaker image is built, continuing")

    def get_stats(self):
        self.logger.info(
            "Current number of scenarios executed: {}".format(self.scenarios_count))
        self.logger.info(
            "Current number of scenarios passed: {}".format(self.pass_scenarios))
        self.logger.info(
            "Current number of scenarios failed: {}".format(self.fail_scenarios))

    def final_stats(self, total):
        self.logger.info("Total scenarios enabled by user: {}".format(total))
        self.logger.info(
            "Total number of scenarios executed: {}".format(self.scenarios_count))
        self.logger.info(
            "Total number of scenarios passed: {}".format(self.pass_scenarios))
        self.logger.info(
            "Total number of scenarios failed: {}".format(self.fail_scenarios))

    def set_scenario(self, scenario):
        fname = scenario['file']
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
            data['execution']['progression'] = scenario['progression']
        else:
            data['execution']['progression'] = default_progression
        data['execution']['tests'] = [d for d in data['execution']
                                      ['tests'] if d.get('class') == "iperf_graph"]
        if "time" in scenario:
            data['execution']['tests'][0]['time'] = scenario['time']
        else:
            data['execution']['tests'][0]['time'] = default_time
        with open(fname, 'w') as yaml_file:
            yaml_file.write(yaml.dump(data, default_flow_style=False))

    def get_uuidlist(self, data):
        uuidlist = []
        for key in data['records'].iterkeys():
            uuidlist.append(key)
        return uuidlist

    def result_check(self, result_dir, test_name, scenario):
        outputfile = os.path.join(result_dir, test_name + "." + "json")
        error = False
        with open(outputfile) as data_file:
            data = json.load(data_file)
        uuidlist = self.get_uuidlist(data)
        for uuid in uuidlist:
            if data['records'][uuid]['status'] != "ok":
                error = True
        if error:
            self.logger.error("Failed scenario: {}".format(scenario['name']))
            self.logger.error("saved log to: {}.log".format(
                os.path.join(result_dir, test_name)))
            self.fail_scenarios += 1
        else:
            self.logger.info("Completed Scenario: {}".format(scenario['name']))
            self.logger.info("Saved report to: {}".format(
                os.path.join(result_dir, test_name + "." + "html")))
            self.logger.info("saved log to: {}.log".format(
                os.path.join(result_dir, test_name)))
            self.pass_scenarios += 1

    def run_scenario(self, scenario, result_dir, test_name):
        filename = scenario['file']
        server_endpoint = self.config['shaker']['server']
        port_no = self.config['shaker']['port']
        flavor = self.config['shaker']['flavor']
        venv = self.config['shaker']['venv']
        shaker_region = self.config['shaker']['shaker_region']
        timeout = self.config['shaker']['join_timeout']
        cmd_1 = (
            "source {}/bin/activate; source /home/stack/overcloudrc").format(venv)
        cmd_2 = ("shaker --server-endpoint {0}:{1} --flavor-name {2} --scenario {3}"
                 " --os-region-name {7} --agent-join-timeout {6}"
                 " --report {4}/{5}.html --output {4}/{5}.json"
                 " --debug > {4}/{5}.log 2>&1").format(server_endpoint,
                                                       port_no, flavor, filename, result_dir, test_name, timeout, shaker_region)
        cmd = ("{}; {}").format(cmd_1, cmd_2)
        from_ts = int(time.time() * 1000)
        if 'sleep_before' in self.config['shaker']:
            time.sleep(self.config['shaker']['sleep_before'])
        self.tools.run_cmd(cmd)
        self.scenarios_count += 1
        self.result_check(result_dir, test_name, scenario)
        if 'sleep_after' in self.config['shaker']:
            time.sleep(self.config['shaker']['sleep_after'])
        to_ts = int(time.time() * 1000)
        # Snapshotting
        self.grafana.print_dashboard_url(from_ts, to_ts, test_name)
        self.grafana.log_snapshot_playbook_cmd(
            from_ts, to_ts, result_dir, test_name)
        self.grafana.run_playbook(from_ts, to_ts, result_dir, test_name)

    def run_shaker(self):
        self.logger.info("Starting Shaker workloads")
        time_stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.logger.debug("Time Stamp (Prefix): {}".format(time_stamp))
        scenarios = self.config.get('shaker')['scenarios']
        self.shaker_checks()
        scen_length = len(scenarios)
        scen_enabled = 0
        if scen_length > 0:
            for scenario in scenarios:
                if scenario['enabled']:
                    scen_enabled += 1
                    self.logger.info("Scenario: {}".format(scenario['name']))
                    self.set_scenario(scenario)
                    self.logger.debug("Set Scenario File: {}".format(
                        scenario['file']))
                    result_dir = self.tools.create_results_dir(
                        self.config['browbeat'][
                            'results'], time_stamp, "shaker",
                        scenario['name'])
                    time_stamp1 = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    test_name = "{}-browbeat-{}-{}".format(time_stamp1,
                                                           "shaker", scenario['name'])
                    self.run_scenario(scenario, result_dir, test_name)
                    self.get_stats()
                else:
                    self.logger.info(
                        "Skipping {} as scenario enabled: false".format(scenario['name']))
            self.final_stats(scen_enabled)
        else:
            self.logger.error(
                "Configuration file contains no shaker scenarios")

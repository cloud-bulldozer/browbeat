from Tools import Tools
import yaml
import logging
import datetime
import os

class Shaker:
    def __init__(self, config):
        self.logger=logging.getLogger('browbeat.Shaker')
        self.config = config
        self.tools = Tools(self.config)
        self.fail_scenarios =  0
        self.pass_scenarios = 0
        self.scenarios_count = 0

    def shaker_checks(self):
        cmd="source /home/stack/overcloudrc; glance image-list | grep shaker-image"
        if self.tools.run_cmd(cmd) == None:
            self.logger.error("Shaker Image is not built, try again")
            exit(1)
        else:
            self.logger.info("Shaker image is built, continuing")

    def get_stats(self):
        self.logger.info("Current number of scenarios executed: {}".format(self.scenarios_count))
        self.logger.info("Current number of scenarios passed: {}".format(self.pass_scenarios))
        self.logger.info("Current number of scenarios failed: {}".format(self.fail_scenarios))

    def final_stats(self, total):
        self.logger.info("Total scenarios enabled by user: {}".format(total))
        self.logger.info("Total number of scenarios executed: {}".format(self.scenarios_count))
        self.logger.info("Total number of scenarios passed: {}".format(self.pass_scenarios))
        self.logger.info("Total number of scenarios failed: {}".format(self.fail_scenarios))


    def set_scenario(self, config, scenario):
      fname = config['shaker']['scenarios'][scenario]['file']
      stream = open(fname, 'r')
      data = yaml.load(stream)
      stream.close()
      default_placement = "double_room"
      default_density = 1
      default_compute = 1
      default_progression = "linear"
      if "placement" in config['shaker']['scenarios'][scenario]:
          data['deployment']['accommodation'][1] = config['shaker']['scenarios'][scenario]['placement']
      else:
          data['deployment']['accommodation'][1] = default_placement
      if "density" in config['shaker']['scenarios'][scenario]:
          data['deployment']['accommodation'][2]['density'] = config['shaker']['scenarios'][scenario]['density']
      else:
          data['deployment']['accommodation'][2]['density'] = default_density
      if "compute" in config['shaker']['scenarios'][scenario]:
          data['deployment']['accommodation'][3]['compute_nodes'] = config['shaker']['scenarios'][scenario]['compute']
      else:
          data['deployment']['accommodation'][3]['compute_nodes'] = default_compute
      if "progression" in config['shaker']['scenarios'][scenario]:
          data['execution']['progression'] = config['shaker']['scenarios'][scenario]['progression']
      else:
          data['execution']['progression'] = default_progression
      data['execution']['tests']=[d for d in data['execution']['tests'] if d.get('class') == "iperf_graph"]
      with open(fname, 'w') as yaml_file:
          yaml_file.write( yaml.dump(data, default_flow_style=False))

    def run_scenario(self, filename, result_dir, test_name, scenario):
        server_endpoint = self.config['shaker']['server']
        port_no = self.config['shaker']['port']
        flavor = self.config['shaker']['flavor']
        venv = self.config['shaker']['venv']
        cmd_1 = ("source {}/bin/activate; source /home/stack/overcloudrc").format(venv)
        cmd_2=("shaker --server-endpoint {0}:{1} --flavor-name {2} --scenario {3}"
               " --os-region-name regionOne --no-report-on-error"
               " --report {4}/{5}.html --output {4}/{5}.json"
               " --debug > {4}/{5}.log 2>&1").format(server_endpoint,
               port_no, flavor, filename, result_dir, test_name)
        cmd = ("{}; {}").format(cmd_1, cmd_2)
        self.tools.run_cmd(cmd)
        self.scenarios_count += 1
        print os.path.join(result_dir,test_name)
        if os.path.isfile(os.path.join(result_dir,test_name + "." + "html")):
            self.logger.info("Completed Scenario: {}".format(scenario))
            self.logger.info("Saved report to: {}".format(os.path.join(result_dir, test_name + "." + "html")))
            self.logger.info("saved log to: {}.log".format(os.path.join(result_dir, test_name)))
            self.pass_scenarios += 1

        else:
            self.logger.error("Failed scenario: {}".format(scenario))
            self.logger.error("saved log to: {}.log".format(os.path.join(result_dir, test_name)))
            self.fail_scenarios += 1

    def run_shaker(self):
        self.logger.info("Starting Shaker workloads")
        time_stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.logger.debug("Time Stamp (Prefix): {}".format(time_stamp))
        _scenarios=self.config.get('shaker')['scenarios']
        self.shaker_checks()
        scen_length=len(_scenarios)
        scen_enabled = 0
        if scen_length > 0:
            for scenario in sorted(_scenarios):
                 if _scenarios[scenario]['enabled']:
                     scen_enabled += 1
                     self.logger.info("Scenario: {}".format(scenario))
                     self.set_scenario(self.config, scenario)
                     self.logger.debug("Set Scenario File: {}".format(
                                _scenarios[scenario]['file']))
                     result_dir = self.tools.create_results_dir(
                                self.config['browbeat']['results'], time_stamp, "shaker",
                                scenario)
                     time_stamp1 = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                     test_name = "{}-browbeat-{}-{}".format(time_stamp1,
                                        "shaker", scenario)
                     self.run_scenario(_scenarios[scenario]['file'], result_dir, test_name, scenario)
                     self.get_stats()
                 else:
                     self.logger.info("Skipping {} as scenario enabled: false".format(scenario))
            self.final_stats(scen_enabled)
        else:
            self.logger.error("Configuration file contains no shaker scenarios")

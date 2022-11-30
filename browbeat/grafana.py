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

import logging
import yaml
import json
import requests
from requests.auth import HTTPBasicAuth

class Grafana(object):

    def __init__(self, config):
        self.logger = logging.getLogger('browbeat.grafana')
        self.config = config
        self.cloud_name = self.config['browbeat']['cloud_name']
        self.host = self.config['grafana']['host']
        self.port = self.config['grafana']['port']
        self.grafana_url = {}

    def grafana_urls(self):
        return self.grafana_url

    def create_grafana_urls(self, time):
        if 'grafana' in self.config and self.config['grafana']['enabled']:
            from_ts = time['from_ts']
            to_ts = time['to_ts']
            url = 'http://{}:{}/dashboard/db/'.format(
                self.host, self.port)
            for dashboard in self.config['grafana']['dashboards']:
                self.grafana_url[dashboard] = '{}{}?from={}&to={}&var-Cloud={}'.format(
                    url,
                    dashboard,
                    from_ts,
                    to_ts,
                    self.cloud_name)

    def print_dashboard_url(self, test_name):
        for dashboard in self.grafana_url:
            self.logger.debug(
                '{} - Grafana Dashboard {} URL: {}'.format(
                    test_name,
                    dashboard,
                    self.grafana_url[dashboard]))

    def create_grafana_annotations(self, start_timestamp, end_timestamp, scenario_name,
                                   test_name, times, concurrency):
        """Create annotations on Grafana dashboard for a given scenario
        :param start_timestamp: epoch time when scenario started running
        :param end_timestamp: epoch time when scenario finished running
        :param scenario_name: str, name of Browbeat scenario
        :param test_name: str, name of test in Rally DB
        :param times: int, times value from Rally
        :param concurrency: int, concurrency value from Rally
        """
        with open("ansible/install/group_vars/all.yml", "r") as group_vars_file:
            group_vars = yaml.safe_load(group_vars_file)

        required_fields = ["grafana_host", "grafana_port", "grafana_username",
                           "grafana_dashboard_uid", "cloud_prefix"]

        for field in required_fields:
            if group_vars[field] is None:
                raise Exception("""{} in ansible/install/group_vars/all.yml is
                                required to create grafana annotations""".format(
                                field))

        grafana_host = group_vars["grafana_host"]
        grafana_port = group_vars["grafana_port"]
        grafana_username = group_vars["grafana_username"]
        grafana_password = group_vars["grafana_password"]
        grafana_dashboard_uid = group_vars["grafana_dashboard_uid"]
        cloud_prefix = group_vars["cloud_prefix"]

        request_body = {"dashboardUID": grafana_dashboard_uid, "time": start_timestamp,
                        "timeEnd": end_timestamp,
                        "tags": [cloud_prefix,
                                 "times: {}".format(times),
                                 "concurrency: {}".format(concurrency),
                                 # test_name_prefix contains a time in the
                                 # yyyymmdd-hhmmss format. This prefix can
                                 # be used to locate Browbeat results of runs easily.
                                 "test_name_prefix: {}".format("-".join(test_name.split("-")[:2]))],
                        "text": scenario_name}

        headers = {'Content-type':'application/json', 'Accept':'application/json'}

        response = requests.post(url="http://{}:{}/api/annotations".format(
                                 grafana_host, grafana_port), data=json.dumps(request_body),
                                 auth=HTTPBasicAuth(grafana_username, grafana_password),
                                 headers=headers)

        if response.status_code == 200:
            self.logger.info("Grafana annotation created successfully for scenario {}".format(
                             scenario_name))
        else:
            self.logger.warning("Grafana annotation creation failed : {}".format(
                                response.json()))

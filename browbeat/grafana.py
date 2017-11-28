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

import logging
import subprocess


class Grafana:
    def __init__(self, config):
        self.logger = logging.getLogger('browbeat.Grafana')
        self.config = config
        self.cloud_name = self.config['grafana']['cloud_name']
        self.hosts_file = self.config['ansible']['hosts']
        self.grafana_ip = self.config['grafana']['grafana_ip']
        self.grafana_port = self.config['grafana']['grafana_port']
        self.playbook = self.config['ansible']['grafana_snapshot']

    def get_extra_vars(self, from_ts, to_ts, result_dir, test_name):
        extra_vars = 'grafana_ip={} '.format(self.config['grafana']['grafana_ip'])
        extra_vars += 'grafana_port={} '.format(self.config['grafana']['grafana_port'])
        extra_vars += 'grafana_api_key={} '.format(self.config['grafana']['snapshot']['grafana_api_key'])
        extra_vars += 'from={} '.format(from_ts)
        extra_vars += 'to={} '.format(to_ts)
        extra_vars += 'results_dir={}/{} '.format(result_dir, test_name)
        extra_vars += 'var_cloud={} '.format(self.cloud_name)
        if self.config['grafana']['snapshot']['snapshot_compute']:
            extra_vars += 'snapshot_compute=true '
        return extra_vars

    def print_dashboard_url(self, from_ts, to_ts, test_name):
        if 'grafana' in self.config and self.config['grafana']['enabled']:
            url = 'http://{}:{}/dashboard/db/'.format(self.grafana_ip, self.grafana_port)
            for dashboard in self.config['grafana']['dashboards']:
                full_url = '{}{}?from={}&to={}&var-Cloud={}'.format(
                    url, dashboard, from_ts, to_ts, self.cloud_name)
                self.logger.info('{} - Grafana URL: {}'.format(test_name, full_url))

    def log_snapshot_playbook_cmd(self, from_ts, to_ts, result_dir, test_name):
        if 'grafana' in self.config and self.config['grafana']['enabled']:
            extra_vars = self.get_extra_vars(from_ts, to_ts, result_dir, test_name)
            snapshot_cmd = 'ansible-playbook -i {} {} -e "{}"'.format(
                self.hosts_file, self.playbook, extra_vars)
            self.logger.info('Snapshot command: {}'.format(snapshot_cmd))

    def run_playbook(self, from_ts, to_ts, result_dir, test_name):
        if 'grafana' in self.config and self.config['grafana']['enabled']:
            if self.config['grafana']['snapshot']['enabled']:
                extra_vars = self.get_extra_vars(from_ts, to_ts, result_dir, test_name)
                subprocess_cmd = ['ansible-playbook', '-i', self.hosts_file, self.playbook, '-e',
                    '{}'.format(extra_vars)]
                snapshot_log = open('{}/snapshot.log'.format(result_dir), 'a+')
                self.logger.info('Running ansible to create snapshots for: {}'.format(test_name))
                subprocess.Popen(subprocess_cmd, stdout=snapshot_log, stderr=subprocess.STDOUT)

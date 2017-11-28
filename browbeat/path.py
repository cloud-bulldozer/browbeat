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
import os


_logger = logging.getLogger('browbeat.path')

# Browbeat's project modules path, typically /home/stack/browbeat/browbeat
browbeat_project_path = os.path.dirname(os.path.realpath(__file__))

# Path to Browbeat, typically /home/stack/browbeat
browbeat_path = os.path.abspath(os.path.join(browbeat_project_path, os.pardir))

# Base Path, typically /home/stack
base_path = os.path.abspath(os.path.join(browbeat_path, os.pardir))

conf_path = os.path.join(browbeat_path, 'conf')

conf_schema_path = os.path.join(browbeat_project_path, 'schema')

log_path = os.path.join(browbeat_path, 'log')

results_path = os.path.join(browbeat_path, 'results')

def get_overcloudrc():
    """Check the several expected locations for the overcloudrc file:
    * $base_path/overcloudrc
    * $browbeat_path/overcloudrc
    """
    paths = [
        os.path.join(base_path, 'overcloudrc'),
        os.path.join(browbeat_path, 'overcloudrc')
    ]
    for overcloudrc_file in paths:
        if os.path.exists(overcloudrc_file):
            return overcloudrc_file
        else:
            _logger.debug("overcloudrc not found in {}".format(overcloudrc_file))
    _logger.error('overcloudrc file can not be found')

def get_workload_venv(workload, path_activate):
    """Check the several expected locations for a workload's venv and return the existing venv:
    * $base_path/$workload-venv
    * $base_path/.$workload-venv
    * $browbeat_path/.$workload-venv
    """
    paths = [
        os.path.join(base_path, '{}-venv'.format(workload)),
        os.path.join(base_path, '.{}-venv'.format(workload)),
        os.path.join(browbeat_path, '.{}-venv'.format(workload))
    ]
    for workload_venv_path in paths:
        if os.path.isdir(workload_venv_path):
            if path_activate and os.path.exists(os.path.join(workload_venv_path, 'bin/activate')):
                return os.path.join(workload_venv_path, 'bin/activate')
            else:
                return workload_venv_path
        else:
            _logger.debug("{} not installed in {}".format(workload, workload_venv_path))
    _logger.error('{} does not appear to be installed correctly'.format(workload))

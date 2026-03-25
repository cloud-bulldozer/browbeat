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

import datetime
import logging
import os
import re
import sys
import time
import yaml

import browbeat.tools
from browbeat import elastic
from browbeat import grafana
from browbeat.path import get_workload_venv
from browbeat.path import results_path
from browbeat.workloads import base


class Workflow(base.WorkloadBase):
    """Workflow scenario workload for user-defined OpenStack test sequences"""

    def __init__(self, config, result_dir_ts):
        """Initialize workflow workload with config and result directory timestamp

        Args:
            config (dict): Browbeat configuration dictionary
            result_dir_ts (str): Timestamp for result directory
        """
        self.logger = logging.getLogger('browbeat.workflow')
        self.config = config
        self.result_dir_ts = result_dir_ts
        self.tools = browbeat.tools.Tools(self.config)
        self.grafana = grafana.Grafana(self.config)
        self.elastic = elastic.Elastic(self.config, self.__class__.__name__.lower())
        self.os_clients = None
        self.state = {}

    def _setup_rally_venv_path(self):
        """Add rally-venv site-packages to sys.path so rally_openstack is importable.

        Browbeat runs from browbeat-venv, but rally_openstack and its
        dependencies live in the rally-venv. Rally workloads handle this by
        shelling out (source .rally-venv/bin/activate; rally ...), but
        workflow needs direct Python imports. This method adds the rally-venv
        site-packages to sys.path so the imports work.
        """
        rally_venv = get_workload_venv('rally', False)
        if not rally_venv:
            self.logger.warning("Rally venv not found, assuming rally_openstack "
                                "is available in current environment")
            return

        # Find the site-packages directory inside the rally venv
        lib_path = os.path.join(rally_venv, 'lib')
        if not os.path.isdir(lib_path):
            self.logger.warning("Rally venv lib dir not found: {}".format(lib_path))
            return

        for pydir in os.listdir(lib_path):
            site_packages = os.path.join(lib_path, pydir, 'site-packages')
            if os.path.isdir(site_packages) and site_packages not in sys.path:
                sys.path.insert(0, site_packages)
                self.logger.info("Added rally-venv site-packages to sys.path: {}".format(
                    site_packages))
                return

        self.logger.warning("Could not find site-packages in rally venv: {}".format(rally_venv))

    def _load_openstack_credentials(self):
        """Load OpenStack credentials from overcloudrc or clouds.yaml.

        Reads credentials from the same source files used by Ansible to create
        the Rally deployment:
        - RHOSP/TripleO: overcloudrc file with export OS_* statements
        - RHOSO: overcloudrc has OS_CLOUD=default, credentials in clouds.yaml

        See: ansible/install/roles/rally/tasks/main.yml
             ansible/install/roles/browbeat-rhoso-prep/tasks/main.yml
        """
        from browbeat.path import get_overcloudrc
        from browbeat.path import base_path

        overcloudrc = get_overcloudrc()
        if not overcloudrc:
            self.logger.debug("overcloudrc file not found")
            return False

        # Source the overcloudrc and capture all OS_* env vars
        cmd = "source {} && env | grep ^OS_".format(overcloudrc)
        result = self.tools.run_cmd(cmd)

        if result['rc'] != 0:
            self.logger.debug("Failed to source overcloudrc: {}".format(result['stderr']))
            return False

        # Parse OS_* variables from output
        for line in result['stdout'].splitlines():
            if '=' in line:
                key, _, value = line.partition('=')
                os.environ[key] = value

        # Check if this is a RHOSO deployment (overcloudrc only has OS_CLOUD=default)
        # In RHOSO, credentials come from clouds.yaml
        if os.environ.get('OS_CLOUD') and not os.environ.get('OS_AUTH_URL'):
            self.logger.debug("RHOSO deployment detected, loading from clouds.yaml")
            return self._load_clouds_yaml(base_path)

        if os.environ.get('OS_AUTH_URL'):
            self.logger.info("Loaded OpenStack credentials from overcloudrc")
            return True

        return False

    def _load_clouds_yaml(self, base_path):
        """Load credentials from clouds.yaml for RHOSO deployments.

        RHOSO prep role creates clouds.yaml at $HOME/.config/openstack/clouds.yaml
        with all credentials. Rally deployment is created from keystone-v3.json
        which is generated from the same clouds.yaml.

        See: ansible/install/roles/browbeat-rhoso-prep/tasks/main.yml
        """
        clouds_yaml_path = os.path.join(base_path, '.config', 'openstack', 'clouds.yaml')
        if not os.path.isfile(clouds_yaml_path):
            self.logger.debug("clouds.yaml not found at {}".format(clouds_yaml_path))
            return False

        try:
            with open(clouds_yaml_path, 'r') as f:
                clouds_config = yaml.safe_load(f)
        except Exception as e:
            self.logger.debug("Failed to load clouds.yaml: {}".format(e))
            return False

        cloud_name = os.environ.get('OS_CLOUD', 'default')
        cloud = clouds_config.get('clouds', {}).get(cloud_name, {})
        if not cloud:
            self.logger.debug("Cloud '{}' not found in clouds.yaml".format(cloud_name))
            return False

        auth = cloud.get('auth', {})

        env_mapping = {
            'auth_url': 'OS_AUTH_URL',
            'username': 'OS_USERNAME',
            'password': 'OS_PASSWORD',
            'project_name': 'OS_PROJECT_NAME',
            'user_domain_name': 'OS_USER_DOMAIN_NAME',
            'project_domain_name': 'OS_PROJECT_DOMAIN_NAME',
        }

        for yaml_key, env_key in env_mapping.items():
            value = auth.get(yaml_key)
            if value:
                os.environ[env_key] = str(value)

        # Set non-auth fields
        if cloud.get('region_name'):
            os.environ['OS_REGION_NAME'] = str(cloud['region_name'])

        if cloud.get('insecure'):
            os.environ['OS_INSECURE'] = 'true'

        if os.environ.get('OS_AUTH_URL'):
            self.logger.info("Loaded OpenStack credentials from clouds.yaml (cloud: {})"
                             .format(cloud_name))
            return True

        return False

    def initialize_openstack_clients(self):
        """Initialize OpenStack clients using rally_openstack.osclients.

        Loads credentials from the same source files used to create the
        Rally deployment:
        - RHOSP: overcloudrc with OS_* exports
        - RHOSO: clouds.yaml (overcloudrc only has OS_CLOUD=default)

        Then adds rally-venv site-packages to sys.path and creates
        osclients via create_from_env().
        """
        if self.os_clients is not None:
            return

        self._setup_rally_venv_path()

        # Load OS_* env vars from overcloudrc/clouds.yaml if not already set
        if not os.environ.get('OS_AUTH_URL'):
            self._load_openstack_credentials()

        try:
            from rally.common import cfg
            CONF = cfg.CONF
            # Set http timeout same as rally_cleanup.py to avoid traceback
            CONF.openstack_client_http_timeout = 180.0

            # Suppress InsecureRequestWarning when https_insecure is set
            # Rally does this internally in its subprocess; we need to do it
            # explicitly since we run in the browbeat-venv process
            if os.environ.get('OS_INSECURE', '').lower() == 'true':
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            from rally_openstack.common import osclients
            self.os_clients = osclients.Clients.create_from_env()
            self.logger.info("OpenStack clients initialized successfully")
        except Exception as e:
            self.logger.error("Failed to initialize OpenStack clients: {}".format(e))
            raise

    def run_workload(self, workload, run_iteration):
        """Main entry point - execute all scenarios in workload

        Args:
            workload (dict): Workload configuration from browbeat config
            run_iteration (int): Current iteration number
        """
        self.logger.info("Running Workflow workload: {}".format(workload["name"]))

        # Initialize OpenStack clients once for all scenarios
        self.initialize_openstack_clients()

        for scenario in workload.get("scenarios", []):
            if not scenario.get("enabled", True):
                self.logger.info("{} scenario is disabled".format(scenario.get('name', 'unknown')))
                continue

            scenario_name = scenario["name"]
            scenario_file = scenario["file"]

            self.logger.info("Running Scenario: {}".format(scenario_name))
            self.logger.debug("Scenario File: {}".format(scenario_file))
            self.update_total_scenarios()

            # Create result directory for this scenario
            # This also creates the parent timestamp directory needed by workload_logger
            result_dir = self.tools.create_results_dir(
                results_path,
                self.result_dir_ts,
                self.__class__.__name__.lower(),
                workload["name"],
                scenario_name
            )

            if not result_dir:
                self.logger.error("Failed to create result directory")
                continue

            self.logger.debug("Created result directory: {}".format(result_dir))
            self.workload_logger(self.__class__.__name__)

            # Run the scenario
            self.run_scenario(scenario, result_dir, scenario_name, run_iteration)

    def run_scenario(self, scenario_def, result_dir, scenario_name, run):
        """Execute single scenario with timing

        Args:
            scenario_def (dict): Scenario definition with file path
            result_dir (str): Directory to store results
            scenario_name (str): Name of the scenario
            run (int): Run iteration number
        """
        self.update_total_tests()

        # Load scenario YAML file
        scenario_file = scenario_def["file"]
        if not os.path.isfile(scenario_file):
            self.logger.error("Scenario file not found: {}".format(scenario_file))
            self.update_total_fail_tests()
            return

        try:
            with open(scenario_file, 'r') as f:
                scenario_content = yaml.safe_load(f)
        except Exception as e:
            self.logger.error("Failed to load scenario file {}: {}".format(scenario_file, e))
            self.update_total_fail_tests()
            return

        # Validate scenario content
        if not scenario_content or 'steps' not in scenario_content:
            self.logger.error("Invalid scenario format: missing 'steps' key")
            self.update_total_fail_tests()
            return

        es_ts = datetime.datetime.utcnow()
        test_name = "{}-browbeat-workflow-{}-iteration-{}".format(
            es_ts.strftime("%Y%m%d-%H%M%S"),
            scenario_name,
            run
        )

        self.logger.info("Executing scenario: {}".format(scenario_name))

        # Reset state for this scenario run
        self.state = {
            'variables': scenario_content.get('variables', {}),
            'steps': {},
            'scenario_name': scenario_name
        }

        # Track timing
        from_ts = int(time.time() * 1000)
        from_time = time.time()

        try:
            # Execute all steps in sequence
            success = self.execute_steps(
                scenario_content['steps'], scenario_name,
                result_dir, test_name)

            to_time = time.time()
            to_ts = int(time.time() * 1000)

            # Create Grafana URLs
            self.grafana.create_grafana_urls({'from_ts': from_ts, 'to_ts': to_ts})
            self.grafana.print_dashboard_url(test_name)

            if success:
                self.logger.info("Scenario {} completed successfully".format(scenario_name))
                self.update_total_pass_tests()
                self.get_time_dict(to_time, from_time, scenario_name, test_name,
                                   self.__class__.__name__, "pass", True)
            else:
                self.logger.error("Scenario {} failed".format(scenario_name))
                self.update_total_fail_tests()
                self.get_time_dict(to_time, from_time, scenario_name, test_name,
                                   self.__class__.__name__, "fail", False)

        except Exception as e:
            to_time = time.time()
            self.logger.error("Scenario {} failed with exception: {}".format(scenario_name, e))
            self.update_total_fail_tests()
            self.get_time_dict(to_time, from_time, scenario_name, test_name,
                               self.__class__.__name__, "fail", False)

    def execute_steps(self, steps, scenario_name, result_dir, test_name):
        """Execute scenario steps sequentially with state management

        Args:
            steps (list): List of step definitions
            scenario_name (str): Name of the scenario
            result_dir (str): Directory to store results
            test_name (str): Name of the test run

        Returns:
            bool: True if all steps succeeded, False otherwise
        """
        for step_index, step in enumerate(steps):
            step_name = step.get('name', 'step-{}'.format(step_index))
            self.logger.info("Executing step {}: {}".format(step_index + 1, step_name))

            try:
                step_start = time.time()
                result = self.execute_step(step, step_index)
                step_duration = time.time() - step_start

                # Save result to state if requested
                if step.get('save_as'):
                    self.state[step['save_as']] = result.get('result')

                # Track step execution in state
                self.state['steps'][step_name] = {
                    'success': result.get('success', True),
                    'result': result.get('result'),
                    'duration': step_duration
                }

                # Index step result to Elasticsearch if enabled
                if self.config.get('elasticsearch', {}).get('enabled', False):
                    self.index_step_result(step, step_index, result, step_duration,
                                           scenario_name, test_name, result_dir)

                # Check for failure and on_failure behavior
                if not result.get('success', True):
                    on_failure = step.get('on_failure', 'continue')
                    if on_failure == 'fail':
                        self.logger.error(
                            "Step {} failed, stopping scenario"
                            .format(step_name))
                        return False
                    else:
                        self.logger.warning(
                            "Step {} failed but continuing"
                            .format(step_name))

            except Exception as e:
                self.logger.error("Step {} raised exception: {}".format(step_name, e))
                on_failure = step.get('on_failure', 'continue')
                if on_failure == 'fail':
                    return False

        return True

    def execute_step(self, step, step_index):
        """Execute single operation step

        Args:
            step (dict): Step definition with operation and args
            step_index (int): Index of the step

        Returns:
            dict: Result dictionary with 'success' and 'result' keys
        """
        operation_type = step.get('operation')
        if not operation_type:
            self.logger.error("Step {} missing 'operation' key".format(step_index))
            return {'success': False, 'result': None, 'error': 'Missing operation'}

        # Resolve variables in args
        args = self.resolve_variables(step.get('args', {}))

        # Get and execute operation handler
        handler = self.get_operation_handler(operation_type)
        if not handler:
            self.logger.error("Unknown operation type: {}".format(operation_type))
            return {'success': False, 'result': None, 'error': 'Unknown operation'}

        try:
            result = handler(args, step)
            return {'success': True, 'result': result}
        except Exception as e:
            self.logger.error("Operation {} failed: {}".format(operation_type, e))
            return {'success': False, 'result': None, 'error': str(e)}

    def resolve_variables(self, obj):
        """Resolve Jinja2-style variables in object using state dictionary

        Args:
            obj: Object to resolve (str, dict, list, or primitive)

        Returns:
            Resolved object with variables substituted
        """
        if isinstance(obj, str):
            # Match {{ variable.path }} patterns
            pattern = r'\{\{.*?\}\}'

            def _resolve_match(m):
                # Extract variable path, strip braces and whitespace
                var_path = m.group(0)[2:-2].strip()
                keys = var_path.split('.')

                # First try direct state lookup (for saved step results like network.id)
                try:
                    value = self.state
                    for key in keys:
                        if isinstance(value, dict):
                            value = value[key]
                        else:
                            value = getattr(value, key)
                    return str(value)
                except (KeyError, AttributeError):
                    pass

                # Then try variables dict (for scenario-level variables like network_name)
                try:
                    value = self.state.get('variables', {})
                    for key in keys:
                        if isinstance(value, dict):
                            value = value[key]
                        else:
                            value = getattr(value, key)
                    return str(value)
                except (KeyError, AttributeError) as e:
                    self.logger.warning(
                        "Could not resolve variable {}: {}".format(var_path, e))

                return m.group(0)  # Return original if unresolved

            obj = re.sub(pattern, _resolve_match, obj)
            return obj

        elif isinstance(obj, dict):
            return {k: self.resolve_variables(v) for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self.resolve_variables(item) for item in obj]

        else:
            return obj

    def get_operation_handler(self, operation_type):
        """Return handler function for operation type

        Args:
            operation_type (str): Operation type (e.g., 'nova.boot_server',
                'neutron.create_network')

        Returns:
            callable: Handler function or None if not found
        """
        from workflow import get_all_handlers
        handlers = get_all_handlers(self)
        return handlers.get(operation_type)

    def index_step_result(self, step, step_index, result,
                          duration, scenario_name, test_name,
                          result_dir):
        """Index step result to Elasticsearch

        Args:
            step (dict): Step definition
            step_index (int): Index of the step
            result (dict): Step execution result
            duration (float): Step execution duration in seconds
            scenario_name (str): Name of the scenario
            test_name (str): Name of the test run
            result_dir (str): Directory for results
        """
        es_ts = datetime.datetime.utcnow()
        doc = {
            'timestamp': str(es_ts).replace(" ", "T"),
            'browbeat_uuid': str(elastic.browbeat_uuid),
            'cloud_name': self.config['browbeat'].get('cloud_name', 'openstack'),
            'scenario_name': scenario_name,
            'step_name': step.get('name', 'step-{}'.format(step_index)),
            'step_index': step_index,
            'operation_type': step.get('operation'),
            'status': 'success' if result.get('success') else 'failure',
            'duration': duration,
            'step_result': result.get('result'),
            'error': result.get('error'),
        }

        # Combine with metadata
        doc = self.elastic.combine_metadata(doc)

        # Index to Elasticsearch
        index_status = self.elastic.index_result(doc, test_name, result_dir, 'workflow')
        if not index_status:
            self.update_index_failures()

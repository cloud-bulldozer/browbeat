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

import time

from rally.common import logging
from rally_openstack.scenarios.vm import utils as vm_utils

LOG = logging.getLogger(__name__)


class NovaDynamicScenario(vm_utils.VMScenario):

    def _run_command_with_attempts(self, ssh_connection, cmd, max_attempts=120, timeout=2):
        """Run command over ssh connection with multiple attempts
        :param ssh_connection: ssh connection to run command
        :param cmd: command to run
        :param max_attempts: int, maximum number of attempts to retry command
        :param timeout: int, maximum time to wait for command to complete
        """
        attempts = 0
        while attempts < max_attempts:
            status, out, err = ssh_connection.execute(cmd)
            LOG.info("attempt: {} cmd: {}, status:{}".format(
                attempts, cmd, status))
            if status != 0:
                attempts += 1
                time.sleep(timeout)
            else:
                break
        if (attempts == max_attempts) and (status != 0):
            LOG.info(
                "Error running command %(command)s. "
                "Error %(code)s: %(error)s" %
                {"command": cmd, "code": status, "error": err})
        else:
            LOG.info("Command executed successfully: %(command)s" % {"command": cmd})

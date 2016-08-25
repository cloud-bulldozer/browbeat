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
import subprocess


class Tools:

    def __init__(self, config=None):
        self.logger = logging.getLogger('browbeat.Tools')
        self.config = config
        return None

    # Run command, return stdout as result
    def run_cmd(self, cmd):
        self.logger.debug("Running command : %s" % cmd)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if len(stderr) > 0:
            return None
        else:
            return stdout.strip()

    # Find Command on host
    def find_cmd(self, cmd):
        _cmd = "which %s" % cmd
        self.logger.debug('Find Command : Command : %s' % _cmd)
        command = self.run_cmd(_cmd)
        if command is None:
            self.logger.error("Unable to find %s" % cmd)
            raise Exception("Unable to find command : '%s'" % cmd)
            return False
        else:
            return command.strip()

    def create_run_dir(self, results_dir, run):
        try:
            os.makedirs("%s/run-%s" % (results_dir, run))
            return "%s/run-%s" % (results_dir, run)
        except OSError:
            return False

    # Create directory for results
    def create_results_dir(self, results_dir, timestamp, service, scenario):
        try:
            os.makedirs("{}/{}/{}/{}".format(results_dir,
                                             timestamp, service, scenario))
            self.logger.debug("{}/{}/{}/{}".format(os.path.dirname(results_dir), timestamp, service,
                                                   scenario))
            return "{}/{}/{}/{}".format(os.path.dirname(results_dir), timestamp, service, scenario)
        except OSError:
            return False

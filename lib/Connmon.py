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

import Tools
import os
import logging
import shutil

class Connmon(object):

    def __init__(self, config):
        self.logger = logging.getLogger('browbeat.Connmon')
        self.config = config
        self.tools = Tools.Tools(self.config)
        return None

    # Start connmond
    def start_connmon(self, retry=None):
        self.stop_connmon()
        tool = "connmond"
        connmond = self.tools.find_cmd(tool)
        if not connmond:
            self.logger.error("Unable to find {}".format(tool))
        as_sudo = self.config['connmon']['sudo']
        cmd = ""
        if as_sudo:
            cmd += "sudo "
        cmd += "screen -X -S connmond kill"
        self.tools.run_cmd(cmd)
        self.logger.info("Starting connmond")
        cmd = ""
        cmd += "{} --config /etc/connmon.cfg > /tmp/connmond 2>&1 &".format(
            connmond)
        self.tools.run_cmd(cmd)
        if self.check_connmon_results is False:
            if retry is None:
                self.start_connmon(retry=True)
            else:
                return False
        else:
            return True

    def check_connmon_results(self, result_file='/tmp/connmon_results.csv'):
        return os.path.isfile(result_file)

    # Stop connmond
    def stop_connmon(self):
        self.logger.info("Stopping connmond")
        return self.tools.run_cmd("pkill -9 connmond")

    # Create Connmon graphs
    def connmon_graphs(self, result_dir, test_name):
        cmd = "python graphing/connmonplot.py {}/connmon/{}.csv".format(result_dir,
                                                                        test_name)
        return self.tools.run_cmd(cmd)['stdout']

    # Move connmon results
    def move_connmon_results(self, result_dir, test_name):
        path = "%s/connmon" % result_dir
        if not os.path.exists(path):
            os.mkdir(path)
        return shutil.move("/tmp/connmon_results.csv",
                           "{}/connmon/{}.csv".format(result_dir, test_name))

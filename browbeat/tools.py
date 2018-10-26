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

import copy
import logging
import os
import re
import subprocess

import perfkit
import rally
import shaker
import yoda


class Tools(object):

    def __init__(self, config):
        self.logger = logging.getLogger('browbeat.tools')
        self.config = config

    # Returns true if ping successful, false otherwise
    def is_pingable(self, ip):
        cmd = "ping -c1 " + ip
        result = self.run_cmd(cmd)
        if result['rc'] == 0:
            return True
        else:
            return False

    # Run command async from the python main thread, return Popen handle
    def run_async_cmd(self, cmd):
        FNULL = open(os.devnull, 'w')
        self.logger.debug("Running command : %s" % cmd)
        process = subprocess.Popen(cmd, shell=True, stdout=FNULL)
        return process

    # Run command, return stdout as result
    def run_cmd(self, cmd):
        self.logger.debug("Running command : %s" % cmd)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        output_dict = {}
        output_dict['stdout'] = stdout.strip()
        output_dict['stderr'] = stderr.strip()
        output_dict['rc'] = process.returncode
        if process.returncode > 0:
            self.logger.error("Command {} returned with error".format(cmd))
            self.logger.error("stdout: {}".format(stdout))
            self.logger.error("stderr: {}".format(stderr))
        return output_dict

    # Find Command on host
    def find_cmd(self, cmd):
        _cmd = "which %s" % cmd
        self.logger.debug('Find Command : Command : %s' % _cmd)
        command = self.run_cmd(_cmd)['stdout']
        if command is None:
            self.logger.error("Unable to find %s" % cmd)
            raise Exception("Unable to find command : '%s'" % cmd)
            return False
        else:
            return command.strip()

    # Create directory for results
    def create_results_dir(self, *args):
        the_directory = '/'.join(args)
        if not os.path.isdir(the_directory):
            try:
                os.makedirs(the_directory)
            except OSError as err:
                self.logger.error(
                    "Error creating the results directory: {}".format(err))
                return False
        return the_directory

    def run_workload(self, workload, result_dir_ts, run_iteration):
        """Creates workload object and runs a specific workload.

        :param workload: Dictionary of workload attributes defined by browbeat config
        :param result_dir_ts: Result directory timestamp
        :param run_iteration: Iteration for a specific run
        """
        if workload["type"] == "perfkit":
            workloads = perfkit.PerfKit(self.config, result_dir_ts)
        elif workload["type"] == "rally":
            workloads = rally.Rally(self.config, result_dir_ts)
        elif workload["type"] == "shaker":
            workloads = shaker.Shaker(self.config, result_dir_ts)
        elif workload["type"] == "yoda":
            workloads = yoda.Yoda(self.config, result_dir_ts)
        else:
            self.logger.error("Unknown workload provider: {}".format(workload["type"]))
        workloads.run_workload(copy.deepcopy(workload), run_iteration)

    def check_metadata(self):
        meta = self.config['elasticsearch']['metadata_files']
        for _meta in meta:
            if not os.path.isfile(_meta['file']):
                self.logger.error(
                    "Metadata file {} is not present".format(_meta['file']))
                return False
        return True

    def gather_metadata(self):
        os.putenv("ANSIBLE_SSH_ARGS", " -F {}".format(self.config['ansible']['ssh_config']))

        ansible_cmd = \
            'ansible-playbook -i {} {}' \
            .format(self.config['ansible']['hosts'], self.config['ansible']['metadata_playbook'])
        self.run_cmd(ansible_cmd)
        if not self.check_metadata():
            self.logger.warning("Metadata could not be gathered")
            return False
        else:
            self.logger.info("Metadata about cloud has been gathered")
            return True

    def post_process(self, cli):
        workloads = {}
        workloads['shaker'] = re.compile("shaker")
        workloads['perfkit'] = re.compile("perfkit")
        workloads['rally'] = re.compile("(?!perfkit)|(?!shaker)")
        """ Iterate through dir structure """
        results = {}
        if os.path.isdir(cli.path):
            for dirname, dirnames, files in os.walk(cli.path):
                self.logger.info("Inspecting : %s" % dirname)
                results[dirname] = files
        else:
            self.logger.error("Path does not exist")
            return False

        """ Capture per-workload results """
        workload_results = {}
        json = re.compile(r"\.json")
        if len(results) > 0:
            for path in results:
                for regex in workloads:
                    if re.findall(workloads[regex], path):
                        if regex not in workload_results:
                            workload_results[regex] = []
                        for file in results[path]:
                            if (re.findall(json, file) and
                                    'result_index-es' not in file):
                                workload_results[regex].append(
                                    "{}/{}".format(path, file))
        else:
            self.logger.error("Results are empty")
            return False

        """ Iterate through each workload result, generate ES JSON """
        if len(workload_results) > 0:
            for workload in workload_results:
                if workload is "rally":
                    rally_workload = rally.Rally(self.config)
                    for file in workload_results[workload]:
                        errors, results = rally_workload.file_to_json(file)
                if workload is "shaker":
                    # Stub for Shaker.
                    continue
                if workload is "perfkit":
                    # Stub for PerfKit.
                    continue

    def load_stackrc(self, filepath):
        values = {}
        with open(filepath) as stackrc:
            for line in stackrc:
                pair = line.split('=')
                if 'export' in line:
                    continue
                elif '#' in line:
                    continue
                elif 'if' in line or 'fi' in line:
                    continue
                elif line == '\n':
                    continue

                if '$(' not in line:
                    values[pair[0].strip()] = pair[1].strip()
                elif '$(' in line and 'for key' not in line:
                    values[pair[0].strip()] = \
                        self.run_cmd(
                        "echo " + pair[1].strip())['stdout'].strip()
        return values

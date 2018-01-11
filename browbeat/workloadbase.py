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

import abc
import logging
import os
import yaml

from browbeat.path import results_path


class WorkloadBase(object):
    __metaclass__ = abc.ABCMeta
    logger = logging.getLogger('browbeat.workloadbase')
    success = 0
    failure = 0
    total_tests = 0
    total_scenarios = 0
    index_failures = 0
    browbeat = {}

    def __init__(self):
        self.result_dir_ts = ""

    @abc.abstractmethod
    def run_workload(self, workload, run_iteration):
        pass

    def update_total_scenarios(self):
        WorkloadBase.total_scenarios += 1

    def update_total_tests(self):
        WorkloadBase.total_tests += 1

    def update_total_pass_tests(self):
        WorkloadBase.success += 1

    def update_total_fail_tests(self):
        WorkloadBase.failure += 1

    def update_index_failures(self):
        WorkloadBase.index_failures += 1

    def workload_logger(self, workload):
        workload_result_dir = os.path.join(results_path, self.result_dir_ts)
        if not os.path.isfile("{}/browbeat-{}-run.log".format(workload_result_dir, workload)):
            filehandler = logging.FileHandler(
                "{}/browbeat-{}-run.log".format(workload_result_dir, workload))
            filehandler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)5s - %(message)s')
            filehandler.setFormatter(formatter)
            self.logger.addHandler(filehandler)

    def get_time_dict(self, to_time, from_time, benchmark, test_name, workload, status,
                      index_status="disabled"):
        time_diff = (to_time - from_time)
        if workload not in WorkloadBase.browbeat:
            WorkloadBase.browbeat[workload] = {}
        if benchmark not in WorkloadBase.browbeat[workload]:
            WorkloadBase.browbeat[workload][benchmark] = {}
        if 'tests' not in WorkloadBase.browbeat[workload][benchmark]:
            WorkloadBase.browbeat[workload][benchmark]['tests'] = []
        if index_status is True:
            index_status = "success"
        elif index_status is False:
            index_status = "failure"
        WorkloadBase.browbeat[workload][benchmark]['tests'].append(
            {'Test name': test_name, 'Time': time_diff, 'Test Status': status,
             'Elasticsearch Indexing': index_status})

    @staticmethod
    def dump_report(result_dir, time_stamp):
        with open(os.path.join(result_dir, time_stamp + '.' + 'report'), 'w') as yaml_file:
            yaml_file.write("Browbeat Report Card\n")
            if not WorkloadBase.browbeat:
                yaml_file.write("No tests were enabled")
            else:
                yaml_file.write(
                    yaml.dump(WorkloadBase.browbeat, default_flow_style=False))

    @staticmethod
    def display_summary():
        WorkloadBase.logger.info("Total scenarios executed:{}".format(
            WorkloadBase.total_scenarios))
        WorkloadBase.logger.info("Total tests executed:{}".format(WorkloadBase.total_tests))
        WorkloadBase.logger.info("Total tests passed:{}".format(WorkloadBase.success))
        WorkloadBase.logger.info("Total tests failed:{}".format(WorkloadBase.failure))

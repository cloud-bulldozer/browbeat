from abc import ABCMeta, abstractmethod
import os
import logging
import yaml
import collections
class WorkloadBase:
    __metaclass__ = ABCMeta
    success = 0
    failure = 0
    total_tests = 0
    total_scenarios = 0
    browbeat = {}

    @abstractmethod
    def update_scenarios(self):
        pass

    @abstractmethod
    def update_tests(self):
        pass

    @abstractmethod
    def update_pass_tests(self):
        pass

    @abstractmethod
    def update_fail_tests(self):
        pass

    def update_total_scenarios(self):
        WorkloadBase.total_scenarios += 1

    def update_total_tests(self):
        WorkloadBase.total_tests += 1

    def update_total_pass_tests(self):
        WorkloadBase.success += 1

    def update_total_fail_tests(self):
        WorkloadBase.failure += 1

    def workload_logger(self, result_dir, workload):
        base = result_dir.split('/')
        if not os.path.isfile("{}/{}/browbeat-{}-run.log".format(base[0], base[1], workload)):
            file = logging.FileHandler(
                "{}/{}/browbeat-{}-run.log".format(base[0], base[1], workload))
            file.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)5s - %(message)s')
            file.setFormatter(formatter)
            self.logger.addHandler(file)
        return None

    def get_time_dict(self, to_time, from_time, benchmark, test_name, workload, status):
        time_diff = (to_time - from_time)
        if workload not in WorkloadBase.browbeat:
            WorkloadBase.browbeat[workload] = {}
        if benchmark not in WorkloadBase.browbeat[workload]:
            WorkloadBase.browbeat[workload][benchmark] = {}
        if 'tests' not in WorkloadBase.browbeat[workload][benchmark]:
            WorkloadBase.browbeat[workload][benchmark]['tests'] = []
        WorkloadBase.browbeat[workload][benchmark]['tests'].append(
            {'Test name': test_name, 'Time': time_diff, 'status': status})

    @staticmethod
    def print_report(result_dir, time_stamp):
        with open(os.path.join(result_dir,time_stamp + '.' + 'report'), 'w') as yaml_file:
            yaml_file.write("Browbeat Report Card\n")
            if not WorkloadBase.browbeat:
                yaml_file.write("No tests were enabled")
            else:
                yaml_file.write(yaml.dump(WorkloadBase.browbeat, default_flow_style=False))

    @staticmethod
    def print_summary():
        print("Total scenarios executed:{}".format(WorkloadBase.total_scenarios))
        print("Total tests executed:{}".format(WorkloadBase.total_tests))
        print("Total tests passed:{}".format(WorkloadBase.success))
        print("Total tests failed:{}".format(WorkloadBase.failure))

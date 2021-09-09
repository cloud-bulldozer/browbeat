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

import os
import subprocess

import dynamic_utils


class ShiftStackDynamicScenario(dynamic_utils.NovaUtils,
                                dynamic_utils.NeutronUtils,
                                dynamic_utils.LockUtils):
    def run_kube_burner_workload(self, workload, job_iterations, qps, burst):
        """Run kube-burner workloads through e2e-benchmarking
        :param workload: str, kube-burner workload to run
        :param job_iterations: int, number of job iterations
        :param qps: int, queries per second
        :param burst: int, burst value to throttle
        """
        browbeat_dir = os.getcwd()
        os.chdir(
            browbeat_dir + "/ansible/gather/e2e-benchmarking/workloads/kube-burner"
        )
        e2e_benchmarking_dir = os.getcwd()

        script_file_name = "run_" + workload + "_test_fromgit.sh"
        script_file_path = e2e_benchmarking_dir + "/" + script_file_name
        script_file = open(script_file_path, "r")
        updated_file_content = ""

        if workload == "poddensity":
            job_iters_param = "PODS"
        elif workload == "clusterdensity":
            job_iters_param = "JOB_ITERATIONS"
        elif workload == "maxnamespaces":
            job_iters_param = "NAMESPACE_COUNT"
        elif workload == "maxservices":
            job_iters_param = "SERVICE_COUNT"

        for line in script_file:
            if "TEST_JOB_ITERATIONS" in line:
                first_part_of_line = line.split("TEST")[0]
                updated_file_content += (
                    first_part_of_line + "TEST_JOB_ITERATIONS=${" + job_iters_param +
                    ":-" + str(job_iterations) + "}\n"
                )
                updated_file_content += "export QPS=" + str(qps) + "\n"
                updated_file_content += "export BURST=" + str(burst) + "\n"
                updated_file_content += "export CLEANUP_WHEN_FINISH=true\n"
            else:
                updated_file_content += line

        with open(script_file_path, "w") as script_file_writer:
            script_file_writer.write(updated_file_content)

        subprocess.run("./" + script_file_name + " 2>&1 | tee -a log.txt && exit ${PIPESTATUS}",
                       shell=True, check=True, executable="/bin/bash")

        os.chdir(browbeat_dir)

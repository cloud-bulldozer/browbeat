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

from rally.task import atomic


class OcpOnOspDynamicScenario():
    def install_ocp_cluster(self):
        """Installs openshift cluster on openstack"""

        ansible_log_file = "ocp_ansible_iter_{}.log".format(self.context["iteration"])
        cmd = ("ansible-playbook -vvv /home/stack/browbeat/ocp_on_osp/ocp_on_osp.yml &> "
               "/home/stack/ocp_ansible_logs/{}").format(ansible_log_file)

        aname = "ocp_on_osp"
        with atomic.ActionTimer(self, aname):
            proc = subprocess.run(cmd, shell=True)

            msg = "openshift cluster installation has failed"
            if proc.returncode != 0:
                self.assertTrue(False, err_msg=msg)

    def run_kube_burner_workload(self, workload, job_iterations, qps, burst, kubeconfig):
        """Run kube-burner workloads through e2e-benchmarking
        :param workload: str, kube-burner workload to run
        :param job_iterations: int, number of job iterations
        :param qps: int, queries per second
        :param burst: int, burst value to throttle
        :param kubeconfig: str, path to kubeconfig file
        """
        os.chdir(
            self.browbeat_dir + "/ansible/gather/e2e-benchmarking/workloads/kube-burner"
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
            if "/usr/bin/bash" in line:
                updated_file_content += line
                updated_file_content += "export KUBECONFIG=${KUBECONFIG:-"+kubeconfig+"}\n"
            elif "TEST_JOB_ITERATIONS" in line:
                first_part_of_line = line.split("TEST")[0]
                updated_file_content += (
                    first_part_of_line + "TEST_JOB_ITERATIONS=${" + job_iters_param +
                    ":-" + str(job_iterations) + "}\n"
                )
                updated_file_content += "export QPS=" + str(qps) + "\n"
                updated_file_content += "export BURST=" + str(burst) + "\n"
                updated_file_content += "export CLEANUP_WHEN_FINISH=true\n"
            elif ("export KUBECONFIG" not in line and "export QPS" not in line and
                  "export BURST" not in line and "export CLEANUP_WHEN_FINISH" not in line):
                updated_file_content += line

        with open(script_file_path, "w") as script_file_writer:
            script_file_writer.write(updated_file_content)

        subprocess.run("./" + script_file_name + " 2>&1 | tee -a log.txt && exit ${PIPESTATUS}",
                       shell=True, check=True, executable="/bin/bash")

        os.chdir(self.browbeat_dir)

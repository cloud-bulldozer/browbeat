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

from rally import exceptions
from rally.common import logging
from rally.task import atomic
from rally_openstack.common import consts
from rally_openstack.scenarios.cinder import utils as cinder_utils
from rally_openstack.task.scenarios.neutron import utils as neutron_utils
from rally_openstack.task.scenarios.vm import utils as vm_utils
from rally.task import scenario
from rally.task import types
from rally.task import validation
from rally.utils import sshutils
from jinja2 import Environment
from jinja2 import FileSystemLoader
import os

LOG = logging.getLogger(__name__)

@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add(
    "required_services", services=[consts.Service.NEUTRON,
                                   consts.Service.NOVA]
)
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={
        "cleanup@openstack": ["neutron", "nova", "cinder"],
        "keypair@openstack": {},
        "allow_ssh@openstack": None,
    },
    name="BrowbeatPlugin.pbench_fio",
    platform="openstack"
)
class PbenchFio(vm_utils.VMScenario, neutron_utils.NeutronScenario,
                cinder_utils.CinderBasic):
    def run(self, image, flavor, num_vms_per_compute, public_net_name, user,
            pbench_key_url, pbench_config_url, pbench_repo_name, pbench_repo_dir_path,
            volume_size, job_input, block_size, io_depth, start_delay, runtime,
            workload_size, num_jobs, sample, ansible_forks, **kwargs):
        # create log and result directories
        with open('../rally_result_dir_path') as f:
            rally_result_dir_path = f.readline()
        pbench_result_dir = rally_result_dir_path + "/pbench/results"
        pbench_log_dir = rally_result_dir_path + "/pbench/logs"
        os.makedirs(pbench_result_dir)
        os.makedirs(pbench_log_dir)

        # create n/w, use it for guests nd jumphost
        network = self._create_network({})
        subnet = self._create_subnet(network, {})

        # attach external network to the subnet
        router = self._create_router({}, external_gw=public_net_name)
        self._add_interface_router(subnet['subnet'], router['router'])

        # create sg
        sg = self.create_custom_security_group()

        # build jumphost
        LOG.info("Creating Jump Host...")
        jumphost, jumphost_ip, jump_ssh = self.build_jumphost(image, flavor, network,
                                                              public_net_name, user,
                                                              sg, volume_size)
        LOG.info("Jump Host has been successfully provisioned.")

        # create client/guest vms with cinder volume attached
        LOG.info("Building Guest VMs...")
        servers, server_ips = self.create_guests(image, flavor, network, num_vms_per_compute,
                                                 sg, volume_size)
        LOG.info("Guest VMs have been successfully created.")

        # prepare and copy job files to jumphost
        env = Environment(loader=FileSystemLoader(os.getcwd()))
        template_path = './rally/rally-plugins/pbench-fio/templates/read.job.j2'
        template = env.get_template(template_path)
        output_file_path = '../read.job'
        self.render_template(env, template, runtime, io_depth, workload_size,
                             num_jobs, start_delay, output_file_path)
        template_path = './rally/rally-plugins/pbench-fio/templates/write.job.j2'
        template = env.get_template(template_path)
        output_file_path = '../write.job'
        self.render_template(env, template, runtime, io_depth, workload_size,
                             num_jobs, start_delay, output_file_path)
        self.copy_over_ssh("../read.job", "~/read.job", jump_ssh)
        self.copy_over_ssh("../write.job", "~/write.job", jump_ssh)

        # prepare and copy client file
        servers_str = "\n".join([str(i) for i in server_ips])
        client_file_str = f"{servers_str}"
        client_file_str = client_file_str + "\n"
        with open("../client_file", 'w') as file:
            file.write(client_file_str)
        self.copy_over_ssh("../client_file", "~/client_file", jump_ssh)

        # copy pbench repos to jumphost
        self.exec_command_over_ssh("mkdir ~/pbench_repos", jump_ssh)
        repo_names = os.listdir(pbench_repo_dir_path)
        for repo_name in repo_names:
            local_path = pbench_repo_dir_path + "/" + repo_name
            remote_path = "~/pbench_repos/" + repo_name
            self.copy_over_ssh(local_path, remote_path, jump_ssh)

        # prepare and copy necessary files to jumphost
        server_ips.append(list(jumphost.addresses.values())[0][0]['addr'])
        self.prepare_inventory(server_ips, pbench_key_url, pbench_config_url, pbench_repo_name)
        self.copy_over_ssh("/etc/resolv.conf", "~/resolv.conf", jump_ssh)
        self.copy_over_ssh("../pbench_inventory.inv", "~/pbench_inventory.inv", jump_ssh)

        local_path = "./rally/rally-plugins/pbench-fio/ansible/bootstrap.yaml"
        self.copy_over_ssh(local_path, "~/bootstrap.yaml", jump_ssh)

        local_path = ("./rally/rally-plugins/pbench-fio/ansible/"
                      "pbench_agent_install.yaml")
        self.copy_over_ssh(local_path, "~/pbench_agent_install.yaml", jump_ssh)

        local_path = ("./rally/rally-plugins/pbench-fio/"
                      "ansible/pbench_agent_tool_meister_firewall.yml")
        remote_path = "~/pbench_agent_tool_meister_firewall.yml"
        self.copy_over_ssh(local_path, remote_path, jump_ssh)

        # install pbench
        LOG.info("Installing Pbench...")
        exit_code = self.install_pbench(jump_ssh, ansible_forks)
        if exit_code != 0:
            self.copy_pbench_logs(jumphost_ip, user, pbench_log_dir)
            raise exceptions.RallyException("Pbench installation failed. "
                                            "Check logs for more details.")
        LOG.info("Pbench installation has been successful on both jumphost and guests.")

        # run jobs
        LOG.info("Starting FIO jobs...")
        jump_ssh_root = sshutils.SSH("root", jumphost_ip, port=22,
                                     pkey=self.context["user"]["keypair"]["private"])
        exit_code = self.handle_jobs(jump_ssh_root, job_input, block_size, sample)
        if exit_code != 0:
            raise exceptions.RallyException("Fio jobs failed. Check logs for more details.")
        LOG.info("FIO jobs has been successfully executed. "
                 "Find results at {}".format(pbench_result_dir))

        # copy logs and results
        self.copy_pbench_results(jumphost_ip, pbench_result_dir)
        self.copy_pbench_logs(jumphost_ip, user, pbench_log_dir)

    def copy_pbench_results(self, jumphost_ip, pbench_result_dir):
        cmd = f"scp -r -i ../pbench_fio_jumphost_pkey root@{jumphost_ip}:" \
            f"/var/lib/pbench-agent/* {pbench_result_dir}/"
        os.system(cmd)

    def copy_pbench_logs(self, jumphost_ip, user, pbench_log_dir):
        cmd = f"scp -i ../pbench_fio_jumphost_pkey {user}@{jumphost_ip}:" \
            f"~/*.log {pbench_log_dir}/"
        os.system(cmd)

    def render_template(self, env, template, runtime, io_depth, workload_size,
                        num_jobs, start_delay, output_file_path):
        rendered_template = template.render(
            runtime=runtime,
            io_depth=io_depth,
            workload_size=workload_size,
            num_jobs=num_jobs,
            start_delay=start_delay
        )

        with open(output_file_path, 'w') as file:
            file.write(rendered_template)

    def copy_over_ssh(self, local_path, remote_path, jump_ssh):
        command = {
            "local_path": local_path,
            "remote_path": remote_path
        }
        self._run_command_over_ssh(jump_ssh, command)

    def exec_command_over_ssh(self, script_inline, jump_ssh):
        command = {
            "script_inline": script_inline,
            "interpreter": "/bin/sh"
        }
        exit_code, _, _ = self._run_command_over_ssh(jump_ssh, command)
        return exit_code

    @atomic.action_timer("pbench_fio.install_pbench")
    def install_pbench(self, jump_ssh, ansible_forks):
        cmd_str = ("sudo cp ~/pbench_repos/* /etc/yum.repos.d && "
                   "sudo cp ~/resolv.conf /etc/resolv.conf && "
                   "export LANG=C.UTF-8 && "
                   "sudo yum install ansible-core -y &> /dev/null && "
                   "ansible-galaxy collection install pbench.agent &> /dev/null && "
                   "ansible-galaxy collection install ansible.posix &> /dev/null")
        self.exec_command_over_ssh(cmd_str, jump_ssh)

        cmd_str = ("export LANG=C.UTF-8 && "
                   "ansible-playbook -i ~/pbench_inventory.inv -vv -f {} bootstrap.yaml "
                   "&> ~/bootstrap.log".format(ansible_forks))
        exit_code = self.exec_command_over_ssh(cmd_str, jump_ssh)
        if exit_code != 0:
            return exit_code

        cmd_str = ("export LANG=C.UTF-8 && "
                   "export ANSIBLE_ROLES_PATH=$HOME/.ansible/collections/ansible_collections/"
                   "pbench/agent/roles:$ANSIBLE_ROLES_PATH && "
                   "ansible-playbook -i ~/pbench_inventory.inv -vv -f {} "
                   "~/pbench_agent_install.yaml &> "
                   "~/pbench_agent_install.log".format(ansible_forks))
        exit_code = self.exec_command_over_ssh(cmd_str, jump_ssh)
        if exit_code != 0:
            return exit_code

        cmd_str = ("export LANG=C.UTF-8 && "
                   "export ANSIBLE_ROLES_PATH=$HOME/.ansible/collections/ansible_collections/"
                   "pbench/agent/roles:$ANSIBLE_ROLES_PATH && "
                   "ansible-playbook -i ~/pbench_inventory.inv -vv -f {} "
                   "~/pbench_agent_tool_meister_firewall.yml &> "
                   "~/pbench_agent_tool_meister_firewall.log".format(ansible_forks))
        exit_code = self.exec_command_over_ssh(cmd_str, jump_ssh)

        return exit_code

    def handle_jobs(self, jump_ssh_root, job_input, block_size, sample):
        job_input = job_input.lower()
        if len(job_input) == 0:
            raise exceptions.RallyException("Job input required")

        if job_input[0] == 'r':
            exit_code = self.write(jump_ssh_root, block_size, sample)
            if exit_code != 0:
                return exit_code

        for job in job_input:
            if job == 'r':
                exit_code = self.read(jump_ssh_root, block_size, sample)
            else:
                exit_code = self.write(jump_ssh_root, block_size, sample)

            if exit_code != 0:
                return exit_code

        return 0

    @atomic.action_timer("pbench_fio.write_job")
    def write(self, jump_ssh_root, block_size, sample):
        cmd_str = f"export LANG=C.UTF-8 && " \
            f"source /etc/profile.d/pbench-agent.sh && " \
            f"pbench-fio -t write -b {block_size} --client-file /root/client_file " \
            f"--pre-iteration-script=/root/drop-cache.sh --job-file=/root/write.job " \
            f"--sample={sample}"
        return self.exec_command_over_ssh(cmd_str, jump_ssh_root)

    @atomic.action_timer("pbench_fio.read_job")
    def read(self, jump_ssh_root, block_size, sample):
        cmd_str = f"export LANG=C.UTF-8 && " \
            f"source /etc/profile.d/pbench-agent.sh && " \
            f"pbench-fio -t read -b {block_size} --client-file /root/client_file " \
            f"--pre-iteration-script=/root/drop-cache.sh --job-file=/root/read.job " \
            f"--sample={sample}"
        return self.exec_command_over_ssh(cmd_str, jump_ssh_root)

    def build_jumphost(self, image, flavor, tenant_network, public_net_name,
                       user, sg, volume_size):
        kwargs = {}
        kwargs["nics"] = [{"net-id": tenant_network["network"]["id"]}]
        kwargs["security_groups"] = [sg["security_group"]["name"]]

        # build jumphost and attach floating ip(preparing it for ssh access)
        jumphost, jumphost_ip = self._boot_server_with_fip(
            image, flavor, use_floating_ip=True,
            floating_network=public_net_name,
            key_name=self.context["user"]["keypair"]["name"],
            **kwargs)
        self._wait_for_ping(jumphost_ip["ip"])
        pkey = self.context["user"]["keypair"]["private"]
        with open("../pbench_fio_jumphost_pkey", 'w') as file:
            file.write(pkey)
        os.chmod('../pbench_fio_jumphost_pkey', 0o600)

        # Open SSH connection
        jump_ssh = sshutils.SSH(user, jumphost_ip["ip"], port=22, pkey=pkey)

        # Check for connectivity and copy pkey
        self._wait_for_ssh(jump_ssh)
        jump_ssh.run("cat > ~/.ssh/id_rsa", stdin=pkey)
        jump_ssh.execute("chmod 0600 ~/.ssh/id_rsa")

        # attach volume
        volume = self.cinder.create_volume(volume_size)
        self._attach_volume(jumphost, volume)

        return jumphost, jumphost_ip["ip"], jump_ssh

    def create_guests(self, image, flavor, network, num_vms_per_compute, sg, volume_size):
        hypervisors = self._list_hypervisors()
        num_computes = len(hypervisors)
        server_ips = []
        servers = []
        kwargs = {}
        kwargs["nics"] = [{"net-id": network["network"]["id"]}]
        kwargs["security_groups"] = [sg["security_group"]["name"]]
        kwargs["key_name"] = self.context["user"]["keypair"]["name"]

        for i in range(num_computes):
            availability_zone = f"nova:{hypervisors[i].hypervisor_hostname}"
            kwargs["availability_zone"] = availability_zone
            servers_per_compute = self._boot_servers(image, flavor, 1,
                                                     instances_amount=num_vms_per_compute, **kwargs)
            servers.extend(servers_per_compute)

        for server in servers:
            server_ips.append(list(server.addresses.values())[0][0]['addr'])
            # attach volume
            volume = self.cinder.create_volume(volume_size)
            self._attach_volume(server, volume)

        return servers, server_ips

    def create_custom_security_group(self):
        security_group = self._create_security_group()
        msg = "security_group isn't created"
        self.assertTrue(security_group, err_msg=msg)

        # icmp
        security_group_rule_args = {}
        security_group_rule_args["protocol"] = "icmp"
        security_group_rule_args["remote_ip_prefix"] = "0.0.0.0/0"
        security_group_rule = self._create_security_group_rule(
            security_group["security_group"]["id"],
            **security_group_rule_args)
        msg = "security_group_rule isn't created"
        self.assertTrue(security_group_rule, err_msg=msg)

        # tcp
        for port in [22, 6379, 17001, 8080, 8765]:
            security_group_rule_args["protocol"] = "tcp"
            security_group_rule_args["port_range_min"] = port
            security_group_rule_args["port_range_max"] = port
            security_group_rule = self._create_security_group_rule(
                security_group["security_group"]["id"],
                **security_group_rule_args)
            msg = "security_group_rule isn't created"
            self.assertTrue(security_group_rule, err_msg=msg)
        return security_group

    def prepare_inventory(self, server_ips, pbench_key_url, pbench_config_url, pbench_repo_name):
        servers = "\n".join([str(i) for i in server_ips])
        inventory_str = f"[servers]\n{servers}\n\n" \
            f"[servers:vars]\npbench_key_url = {pbench_key_url}\n" \
            f"pbench_config_url = {pbench_config_url}\n" \
            f"pbench_repo_name = {pbench_repo_name}"

        with open("../pbench_inventory.inv", 'w') as file:
            file.write(inventory_str)

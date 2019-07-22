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

import argparse
import json
import os
import sys


import six


class Metadata(object):

    def __init__(self):
        # These are the only groups from the ansible inventory, that we are
        # Interested in
        self._supported_node_types = ['overcloud', 'undercloud']
        pass

    def load_file(self, filename):
        try:
            with open(filename) as f:
                system_data = json.load(f)
        except IOError:
            print("machine_facts.json is missing")
            exit(1)
        return system_data

    def get_hardware_metadata(self, sys_data):
        hard_dict = {}
        for item, dictionary in six.iteritems(sys_data):
            if any(node in sys_data[item]['group_names'] for node in self._supported_node_types):
                if 'hardware_details' not in hard_dict:
                    hard_dict['hardware_details'] = []
                hardware_dict = {}
                hardware_dict['label'] = sys_data[item]['inventory_hostname']
                hardware_dict['virtualization_role'] = sys_data[item]['ansible_virtualization_role']
                hardware_dict['virtualization_type'] = sys_data[item]['ansible_virtualization_type']
                hardware_dict['total_mem'] = sys_data[item][
                    'ansible_memory_mb']['real']['total']
                if 'facter_processorcount' in sys_data[item]:
                    hardware_dict['total_logical_cores'] = sys_data[item][
                        'facter_processorcount']
                else:
                    hardware_dict['total_logical_cores'] = sys_data[item][
                        'facter_processors']['count']
                hardware_dict['os_name'] = sys_data[item]['ansible_distribution'] + \
                    sys_data[item]['ansible_distribution_version']
                hardware_dict['ip'] = sys_data[item]['ansible_default_ipv4']['address']
                hardware_dict['num_interface'] = len(sys_data[item]['ansible_interfaces'])
                hardware_dict['machine_make'] = sys_data[item]['ansible_product_name']
                # facter_processor0 is gone in ansible 2.8
                if 'facter_processor0' in sys_data[item]:
                    hardware_dict['processor_type'] = ' '.join(sys_data[item][
                        'facter_processor0'].split())
                else:
                    hardware_dict['processtor_type'] = sys_data[item][
                        'facter_processors']['models'][0]
                hard_dict['hardware_details'].append(hardware_dict)
        return hard_dict

    def get_environment_metadata(self, sys_data):
        env_dict = {}
        for item, dictionary in six.iteritems(sys_data):
            if 'environment_setup' not in env_dict:
                env_dict['environment_setup'] = {}
            for key, value in six.iteritems(sys_data[item]):
                if 'stockpile_osp_env' in key:
                    for nodes, number in six.iteritems(value):
                        env_dict['environment_setup'][nodes] = number
        return env_dict

    def get_software_metadata(self, sys_data):
        soft_all_dict = []
        bad_output_list = [{},[],""]
        for item, dictionary in six.iteritems(sys_data):
            if any(node in sys_data[item]['group_names'] for node in self._supported_node_types):
                software_dict = {}
                sample_vuln_dict = {}
                node = sys_data[item]['inventory_hostname']
                for key, output in six.iteritems(sys_data[item]):
                    if 'stockpile_yum' in key and output not in bad_output_list:
                        software_dict['repos_enabled'] = {}
                        software_dict['repos_enabled']['repos'] = []
                        for repo in output:
                            if repo['state'] in 'enabled':
                                software_dict['repos_enabled']['repos'].append(repo['repoid'])
                        software_dict['repos_enabled']['node_name'] = node
                    if 'stockpile_cpu_vuln' in key and output not in bad_output_list:
                        if 'vulnerability' not in sample_vuln_dict.keys():
                            sample_vuln_dict['vulnerability'] = {}
                        for vuln in output:
                            vuln = vuln.split('/sys/devices/system/cpu/vulnerabilities/')
                            vuln = vuln[1].split(':', 1)
                            sample_vuln_dict['vulnerability'][vuln[0]] = {}
                            if 'Mitigation: ' in vuln[1]:
                                sample_vuln_dict['vulnerability'][vuln[0]]['mitigation'] = \
                                    vuln[1].split('Mitigation: ')[1]
                            if 'Vulnerable: ' in vuln[1]:
                                vuln_value = vuln[1].split('Vulnerable: ')[1]
                                if vuln_value != "":
                                    sample_vuln_dict['vulnerability'][vuln[0]]['type'] = \
                                        vuln_value
                    if 'stockpile_openstack_' in key:
                        service = key.split('stockpile_openstack_')[1]
                        # Either it's a dict or a value
                        if isinstance(output, dict):
                            if '_' in service:
                                # data from outside config files
                                service = service.split('_', 1)
                                service_name = service[0]
                                key_name = service[1]
                                if service_name not in software_dict.keys():
                                    software_dict[service_name] = {}
                                    software_dict[service_name]['node_name'] = node
                                if key_name not in software_dict[service_name].keys():
                                    software_dict[service_name][key_name] = {}
                                for obj, value in six.iteritems(output):
                                    software_dict[service_name][key_name][obj] = value
                            else:
                                for obj, value in six.iteritems(output):
                                    if obj not in software_dict.keys():
                                        software_dict[obj] = value
                                        software_dict[obj]['node_name'] = node
                                    else:
                                        software_dict[obj].update(value)
                        else:
                            if '_' in service:
                                service = service.split('_')
                            if len(service) > 1:
                                service_name = service[0]
                                key_name = service[1]
                                if service_name not in software_dict.keys():
                                    software_dict[service_name] = {}
                                if "DEFAULT" not in software_dict[service_name].keys():
                                    software_dict[service_name]["DEFAULT"] = {}
                                software_dict[service_name]["DEFAULT"][key_name] = output
                                if 'node_name' not in software_dict[service_name]:
                                    software_dict[service_name]['node_name'] = node
                if 'kernel' not in software_dict.keys():
                    software_dict['kernel'] = {}
                software_dict['kernel']['version'] = sys_data[item]['ansible_kernel']
                software_dict['kernel']['architecture'] = sys_data[item]['ansible_architecture']
                software_dict['kernel']['cpu_vulnerabilities'] = sample_vuln_dict['vulnerability']
                software_dict['kernel']['node_name'] = node
                soft_all_dict.append(software_dict)
        return soft_all_dict

    def write_metadata_file(self, data, filename):
        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(description='Metadata Generation')
    parser.add_argument(dest='path', help='Location of machine-facts')
    args = parser.parse_args()
    _filename = os.path.join(args.path, 'machine_facts.json')
    metadata = Metadata()
    sysdata = metadata.load_file(_filename)
    env_data = metadata.get_environment_metadata(sysdata)

    metadata.write_metadata_file(
        env_data, os.path.join(args.path, 'environment-metadata.json'))
    hardware_data = metadata.get_hardware_metadata(sysdata)
    metadata.write_metadata_file(
        hardware_data, os.path.join(args.path, 'hardware-metadata.json'))
    software_data = metadata.get_software_metadata(sysdata)
    # Just a simple check to ensure that stockpile was able to collect osp data
    check = False
    for node in software_data:
        if "nova" in node.keys():
            check = True
    if not check:
        return "Issue with machine_facts.json, no nova data found."
    metadata.write_metadata_file(
        software_data, os.path.join(args.path, 'software-metadata.json'))


if __name__ == '__main__':
    sys.exit(main())

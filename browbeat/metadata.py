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


class Metadata(object):

    def __init__(self):
        pass

    def load_file(self, filename):
        json_str = None
        try:
            with open(filename) as data:
                json_str = data.read()
        except IOError:
            print("Machine facts json is missing")
            exit(1)
        sys_data = {}
        sys_data['system_data'] = json.loads(json_str)
        return sys_data

    def get_hardware_metadata(self, sys_data):
        hard_dict = {}
        for item in sys_data['system_data']:
            if 'hardware_details' not in hard_dict:
                hard_dict['hardware_details'] = []
            hardware_dict = {}
            hardware_dict['label'] = item['inventory_hostname']
            hardware_dict['virtualization_role'] = item['ansible_virtualization_role']
            hardware_dict['virtualization_type'] = item['ansible_virtualization_type']
            hardware_dict['total_mem'] = item[
                'ansible_memory_mb']['real']['total']
            hardware_dict['total_logical_cores'] = item[
                'facter_processorcount']
            hardware_dict['os_name'] = item['ansible_distribution'] + \
                item['ansible_distribution_version']
            hardware_dict['ip'] = item['ansible_default_ipv4']['address']
            hardware_dict['num_interface'] = len(item['ansible_interfaces'])
            hardware_dict['machine_make'] = item['ansible_product_name']
            hardware_dict['processor_type'] = ' '.join(item['facter_processor0'].split())
            hard_dict['hardware_details'].append(hardware_dict)
        return hard_dict

    def get_environment_metadata(self, sys_data):
        env_dict = {}
        for item in sys_data['system_data']:
            if 'environment_setup' not in env_dict:
                env_dict['environment_setup'] = {}
            for key, value in item.items():
                if 'osp' in key:
                    env_dict['environment_setup'][key] = value
        return env_dict

    def get_software_metadata(self, sys_data):
        soft_all_dict = []
        for item in sys_data['system_data']:
            nodes = ['controller', 'undercloud', 'compute']
            if any(node in item['group_names'] for node in nodes):
                software_dict = {}
                for soft in item:
                    if 'openstack' in soft:
                        """
                        Why _S_? Because Ansible doesn't allow for
                        many seperators. The _S_ was used to mimic
                        a seperator.
                        """
                        service = soft.split('_S_')
                        if len(service) < 2:
                            service = soft.split('_')
                            key = service[2]
                            section = "DEFAULT"
                            service_name = service[1]
                        else:
                            key = service[3]
                            section = service[2]
                            service_name = service[1]

                        node = item['inventory_hostname']

                        if service_name in software_dict:
                            if section in software_dict[service_name]:
                                software_dict[service_name][section][key] = item[soft]
                            else:
                                software_dict[service_name][section] = {}
                                software_dict[service_name][section][key] = item[soft]
                        else:
                            software_dict[service_name] = {}
                            software_dict[service_name]['node_name'] = node
                            software_dict[service_name][section] = {}
                            software_dict[service_name][section][key] = item[soft]

                    node = item['inventory_hostname']
                    software_dict['kernel'] = {}
                    software_dict['kernel']['version'] = item['ansible_kernel']
                    software_dict['kernel']['architecture'] = item['ansible_architecture']
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
    metadata.write_metadata_file(
        software_data, os.path.join(args.path, 'software-metadata.json'))


if __name__ == '__main__':
    sys.exit(main())

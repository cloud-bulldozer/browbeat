#!/usr/bin/env python
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

import sys
import os
import subprocess
# usage: openstack-config-parser.py [service] [output file]

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    output_dict = {}
    output_dict['stdout'] = stdout.strip()
    output_dict['stderr'] = stderr.strip()
    output_dict['rc'] = process.returncode
    return output_dict

def strip_chars(line):
    forbidden_chars = ['#', '\n', '"', '\\', ' ', '<', '>']
    for char in forbidden_chars:
        line = line.replace(char, '')
    return line

def parse_config(serviceName, fileName):
    # a dict containing key/value pairs, last value is what is stored.
    values = {}
    with open(fileName) as config:
        section = None
        for line in config:
            pair = strip_chars(line)
            pair = pair.split('=')
            # excludes any line without a key/val pair
            valid_line = not line.startswith("# ") and \
                         '[' not in line and line != '\n' \
                         and line != '#\n' and "password" \
                         not in line.lower()
            if line.startswith('['):
                section = line.replace('[','').replace(']','').replace('\n','')
            if '#' not in line and valid_line and not section == None and len(pair) == 2:
                pair[0] = strip_chars(pair[0])
                pair[1] = strip_chars(pair[1])
                values["openstack_S_" + serviceName + "_S_" + section + "_S_" + pair[0]] = pair[1]
    return values


def try_type(val):
    try:
        int(val)
        return val
    except (ValueError, TypeError):
        try:
            float(val)
            return val
        except (ValueError, TypeError):
            if type(val) is list:
                return "\"" + str(val) + "\""
            elif val.lower() in ("true", "false"):
                return val
            else:
                return "\"" + val + "\""


def add_conf_location(serviceName, fileName, values): 
    # Stores the exact location we gathered this config from.
    index = "openstack_S_" + serviceName + "_S_" + "Browbeat" + "_S_" + "gather_conf_path"
    if index in values:
        values[index].append(fileName)
    else:
        values[index] = [fileName]

def print_vars_file(values, fileName):
    with open(fileName, 'w') as output:
        for key in values:
            output.write(key + ": " + try_type(values[key]) + "\n")

def is_containerized(service_name):
    out = run_cmd("docker ps")
    if service_name in out['stdout']:
        return True
    else:
        return False

def get_configs_list(path, extension='.conf'):
    configs = []
    for item in os.listdir(path):
        if item.endswith(extension):
            configs.extend([item])
    return configs

def get_neutron_plugin(output, cfg_path):
    plugin = output['openstack_S_neutron_S_DEFAULT_S_core_plugin']
    plugin_path = "{}/plugins/{}/".format(cfg_path, plugin)
    for item in get_configs_list(plugin_path, extension='.ini'):
        full_path = "{}/{}".format(plugin_path,
                                   item)
        output.update(parse_config("neutron-plugin", full_path))
        add_conf_location("neutron", full_path, output)
    return output

def main():
    if len(sys.argv) < 3:
        print("usage: openstack-config-parser.py [service] [output file]")
        exit(1)

    service_name = sys.argv[1]
    outfile = sys.argv[2]

    # This is a list of services that require exceptions from the usual
    # pattern when gathering their config files
    pattern_exceptions = ['glance']
    in_container = is_containerized(service_name)


    if 'undercloud' in service_name:
        cfg_path = "/home/stack"
    elif in_container and service_name not in pattern_exceptions:
        cfg_path = "/var/lib/config-data/puppet-generated/{}/etc/{}".format(
            service_name, service_name)
    # Glance has all configs in a folder named glance_api, ps shows no
    # processes outside of the container, so I assume those are the right
    # configs, even though the container is also named glance-api
    # jkilpatr 7/13/17
    elif in_container and 'glance' in service_name:
        cfg_path = "/var/lib/config-data/glance_api/etc/glance"
    else:
        cfg_path = "/etc/{}".format(service_name)

    print("Parsing all .conf files in {}".format(cfg_path))
    output = {}
    for item in get_configs_list(cfg_path):
        full_path = "{}/{}".format(cfg_path,
                                   item)
        output.update(parse_config(service_name, full_path))
        add_conf_location(service_name, full_path, output)
    # Required to find and load the active neutron plugin file.
    if 'neutron' in service_name:
        output.update(get_neutron_plugin(output, cfg_path))

    print_vars_file(output, outfile)

if __name__ == '__main__':
    sys.exit(main())


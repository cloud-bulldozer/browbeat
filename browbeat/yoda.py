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

# Yet another cloud deployment tool

from collections import deque
import datetime
import json
import logging
import os
import time

from openstack import connection
from openstack import exceptions
try:
    from ostag import ostag
except ImportError:
    ostag = None
import requests

import elastic
import grafana
from path import results_path
import workloadbase
import tools


class Yoda(workloadbase.WorkloadBase):

    def __init__(self, config, result_dir_ts):
        self.logger = logging.getLogger('browbeat.yoda')
        self.config = config
        self.result_dir_ts = result_dir_ts
        self.tools = tools.Tools(self.config)
        self.grafana = grafana.Grafana(self.config)
        self.elastic = elastic.Elastic(self.config, self.__class__.__name__.lower())
        self.error_count = 0
        self.pass_count = 0
        self.test_count = 0
        self.scenario_count = 0

    def get_stats(self):
        self.logger.info(
            "Current number of YODA tests executed: {}".format(
                self.test_count))
        self.logger.info(
            "Current number of YODA tests passed: {}".format(
                self.pass_count))
        self.logger.info(
            "Current number of YODA tests failed: {}".format(
                self.error_count))

    def update_tests(self):
        self.test_count += 1
        self.update_total_tests()

    def update_pass_tests(self):
        self.pass_count += 1
        self.update_total_pass_tests()

    def update_fail_tests(self):
        self.error_count += 1
        self.update_total_fail_tests()

    def update_scenarios(self):
        self.scenario_count += 1
        self.update_total_scenarios()

    def state_tracker_extend(self, state, state_list):
        if state is None:
            return state_list
        elif state_list is None:
            return [state]
        elif state in state_list[-1]:
            return state_list
        else:
            state_list.append(state)
            return state_list

    def node_is_cleaning(self, provision_state):
        ret = provision_state is not None
        ret = ret and 'clean' in provision_state
        ret = ret and 'fail' not in provision_state
        return ret

    def is_cleaning(self, conn):
        for node in conn.bare_metal.nodes():
            if self.node_is_cleaning(node.provision_state):
                return True
        return False

    def failed_cleaning_count(self, conn):
        count = 0
        for node in conn.bare_metal.nodes():
            if self.node_is_cleaning(node.provision_state):
                count += 1
        return count

    def wait_for_clean(self, env_setup, conn):
        wait_time = 1
        # 15 minute timeout
        timeout = (60 * 15)
        while self.is_cleaning(conn):
            # Cleans can fail, so we just try again
            if wait_time % 1000 == 0:
                self.set_ironic_node_state("manage", env_setup, conn)
                time.sleep(30)
                self.set_ironic_node_state("provide", env_setup, conn)
            time.sleep(1)
            wait_time += 1
            if wait_time > timeout:
                self.logger.error("Node Cleaning failed")
                exit(1)

    # Required to use console commands because of this bug
    #  https://bugs.launchpad.net/python-openstacksdk/+bug/1668767
    def set_ironic_node_state(self, state, env_setup, conn, node_uuid=""):
        if node_uuid != "":
            nodes = [node_uuid]
        else:
            nodes = deque(map(lambda node: node.id, conn.bare_metal.nodes()))

        if state == "manage":
            cmd_base = "{} openstack baremetal node manage {}"
            for _ in range(len(nodes)):
                node = nodes.pop()
                node_obj = conn.bare_metal.get_node(node)
                if "manage" not in node_obj.provision_state:
                    nodes.append(node)
        elif state == "provide":
            cmd_base = "{} openstack baremetal node provide {}"
            for _ in range(len(nodes)):
                node = nodes.pop()
                node_obj = conn.bare_metal.get_node(node)
                prov_state = node_obj.provision_state
                if prov_state is not None and "available" not in prov_state:
                    nodes.append(node)
        elif state == "inspect":
            cmd_base = "{} openstack baremetal introspection start {}"
        elif state == "off":
            cmd_base = "{} openstack baremetal node power off {}"
            for _ in range(len(nodes)):
                node = nodes.pop()
                node_obj = conn.bare_metal.get_node(node)
                if "off" not in node_obj.power_state:
                    nodes.append(node)
        elif state == "on":
            cmd_base = "{} openstack baremetal node power on {}"
            for _ in range(len(nodes)):
                node = nodes.pop()
                node_obj = conn.bare_metal.get_node(node)
                if "on" not in node_obj.power_state:
                    nodes.append(node)
        elif state == "delete":
            cmd_base = "{} openstack baremetal node delete {}"
        else:
            self.logger.error(
                "set_ironic_node_state() called with invalid state")
            exit(1)

        for node in nodes:
            cmd = cmd_base.format(env_setup, node)
            self.tools.run_async_cmd(cmd + "\"")
            time.sleep(.5)

    # Gathers metrics on the instack env import
    def import_instackenv(self, filepath, env_setup, conn):
        results = {}
        filepath = os.path.abspath(os.path.expandvars(filepath))
        cmd = "{} openstack overcloud node import {}".format(
            env_setup, filepath)
        start_time = datetime.datetime.utcnow()

        out = self.tools.run_cmd(cmd + "\"")

        nodes = conn.bare_metal.nodes()
        for node in nodes:
            while 'enroll' in node.provision_state:
                node = conn.bare_metal.get_node(node)
                time.sleep(1)

        end_time = datetime.datetime.utcnow()
        results['import_time'] = (end_time - start_time).total_seconds()

        if out['stderr'] == '' or 'Error' not in out['stderr']:
            results['import_status'] = "success"
        else:
            results['import_status'] = "failure"
            self.logger.error("Instackenv import returned 1, printing stderr")
            self.logger.error(out['stderr'])

        return results

    # Introspection with exactly the documented workflow
    def introspection_bulk(self, timeout, env_setup, conn):
        results = {}
        nodes = deque(map(lambda node: node.id, conn.bare_metal.nodes()))
        cmd = "{} openstack overcloud node introspect --all-manageable".format(
            env_setup)
        results['nodes'] = {}

        for node in conn.bare_metal.nodes(details=True):
            results['nodes'][node.id] = {}
            results['nodes'][node.id]["last_error"] = node.last_error
            results['nodes'][node.id]["driver"] = node.driver
            results['nodes'][node.id]["driver_info"] = node.driver_info
            results['nodes'][node.id]["properties"] = node.properties
            results['nodes'][node.id]["failures"] = 0
            results['nodes'][node.id]["state_list"] = None

        self.tools.run_async_cmd(cmd + "\"")

        out = self.watch_introspecting_nodes(nodes, timeout, conn, results)

        failed = out[0]
        results['raw'] = out[1]
        results["failure_count"] = len(failed)
        return results

    def watch_introspecting_nodes(self, nodes, timeout, conn, results):
        start_time = datetime.datetime.utcnow()
        times = []
        timeout = datetime.timedelta(seconds=timeout)

        while len(nodes):
            node = nodes.pop()
            # rate limit
            time.sleep(10)
            try:
                node_obj = conn.bare_metal.get_node(node)
            except exceptions.SDKException:
                self.logger.error(
                    "Ironic endpoint is down, retrying in 10 seconds")
                time.sleep(10)
                continue
            if node_obj is None:
                self.logger.error(
                    "Can't find node %s which existed at the start of "
                    "introspection did you delete it manually?", node)
                continue

            # == works here for string comparison because they are in fact
            # the same object if not changed
            stored_properties = str(
                results['nodes'][node_obj.id]["properties"])
            node_properties = str(node_obj.properties)
            changed = not stored_properties == node_properties

            powered_off = 'off' in node_obj.power_state
            not_cleaning = 'clean' not in node_obj.provision_state
            if changed and powered_off and not_cleaning:

                results['nodes'][node_obj.id]["properties"] = node_obj.properties

                results['nodes'][node_obj.id]["state_list"] = self.state_tracker_extend(
                    node_obj.provision_state, results['nodes'][node_obj.id]["state_list"])

                times.append(
                    (datetime.datetime.utcnow() - start_time).total_seconds())

            elif (datetime.datetime.utcnow() - start_time) > timeout:
                # return currently active node to the deque to be failed
                nodes.appendleft(node)
                for node in nodes:
                    node_obj = conn.bare_metal.get_node(node)

                    results['nodes'][node_obj.id]['failures'] += 1
                    if results['nodes'][node_obj.id]['failures'] > 10:
                        self.logger.error(
                            "Node " + node_obj.id + "has failed more than 10 introspections")
                        self.logger.error(
                            "This probably means it's misconfigured, exiting")
                        exit(1)

                break
            else:
                results['nodes'][node_obj.id]["state_list"] = self.state_tracker_extend(
                    node_obj.provision_state, results['nodes'][node_obj.id]["state_list"])
                nodes.appendleft(node)

        return (nodes, times)

    # Introspection with robust failure handling
    def introspection_individual(self, batch_size, timeout, env_setup, conn):
        nodes = deque(map(lambda node: node.id, conn.bare_metal.nodes()))
        failure_count = 0
        batch = deque()
        results = {}
        results['raw'] = []
        results['nodes'] = {}

        for node in conn.bare_metal.nodes(details=True):
            results['nodes'][node.id] = {}
            results['nodes'][node.id]["last_error"] = node.last_error
            results['nodes'][node.id]["driver"] = node.driver
            results['nodes'][node.id]["driver_info"] = node.driver_info
            results['nodes'][node.id]["properties"] = node.properties
            results['nodes'][node.id]["failures"] = 0
            results['nodes'][node.id]["state_list"] = None

        while len(nodes):
            node = nodes.pop()
            self.set_ironic_node_state("inspect", env_setup, conn, node)
            batch.append(node)
            if len(batch) >= batch_size or (
                    len(nodes) == 0 and len(batch) != 0):
                out = self.watch_introspecting_nodes(
                    batch, timeout, conn, results)
                failed = out[0]
                results['raw'].extend(out[1])
                failure_count = failure_count + len(failed)
                nodes.extend(failed)
                batch.clear()

        results["failure_count"] = failure_count
        return results

    def delete_stack(self, conn):
        wait_time = 0
        # 30 minute timeout
        timeout = (60 * 30)
        try:
            while conn.orchestration.find_stack("overcloud") is not None:
                # Deletes can fail, so we just try again
                if wait_time % 2000 == 0:
                    conn.orchestration.delete_stack("overcloud")
                time.sleep(10)
                wait_time += 10
                if wait_time > timeout:
                    self.logger.error("Overcloud stack delete failed")
                    exit(1)
        except exceptions.SDKException:
            # Recursion is probably the wrong way to handle this
            self.logger.error("Heat failure during overcloud delete, retrying")
            time.sleep(10)
            self.delete_stack(conn)

    def setup_nodes_dict(self, benchmark):
        nodes = {}
        for service in benchmark['cloud']:
            nodes[service['node']] = service['start_scale']
            nodes["previous_" + service['node']] = -1
        return nodes

    def update_nodes_dict(self, benchmark, nodes, changed):
        # update settings for next round, note if changes are made
        step = benchmark['step']
        nodes_added = 0
        for service in benchmark['cloud']:
            node_type = service['node']
            end_scale = service['end_scale']
            nodes["previous_" + node_type] = nodes[node_type]
            if nodes[node_type] < end_scale:
                difference = end_scale - nodes[node_type]
                allowed_difference = step - nodes_added
                add = min(difference, allowed_difference)
                nodes[node_type] += add
                nodes_added += add
                changed = True

        # edge cases, we must round up otherwise we get
        # stuck forever if step is 1, this also means we must
        # violate the step rules to both ensure a valid deployment
        # and progression
        if 'control' in nodes and nodes['control'] == 2:
            nodes['control'] = 3
        if 'ceph' in nodes and nodes['ceph'] > 0 and nodes['ceph'] < 3:
            nodes['ceph'] = 3

        return (nodes, changed)

    def deploy_overcloud(self, start_time, results,
                         ntp_server, conn, env_setup, benchmark):

        if not isinstance(ntp_server, str):
            self.logger.error("Please configure an NTP server!")
            exit(1)

        cmd = env_setup + "openstack overcloud deploy --templates "
        for template in benchmark['templates']:
            cmd = cmd + " " + template + " "
        for service in benchmark['cloud']:
            cmd = cmd + " --" + service['node'] + \
                "-scale " + str(results[service['node']])
        cmd = cmd + " --timeout=" + \
            str(benchmark['timeout']) + " --ntp-server=" + str(ntp_server)

        self.logger.debug("Openstack deployment command is " + cmd)
        results["overcloud_deploy_command"] = cmd
        deploy_process = self.tools.run_async_cmd(cmd + "\"")
        results['cleaning_failures'] = self.failed_cleaning_count(conn)
        results['nodes'] = {}

        while deploy_process.poll() is None:
            time.sleep(5)
            try:
                for node in conn.compute.servers():
                    time.sleep(1)

                    # look for new instances to add to our metadata
                    if node.name not in results['nodes']:
                        results['nodes'][node.name] = {}
                        create_time = datetime.datetime.strptime(
                            node.created_at, "%Y-%m-%dT%H:%M:%SZ")
                        results['nodes'][node.name]['created_at'] = \
                            (create_time - start_time).total_seconds()
                        results['nodes'][node.name]['scheduler_hints'] = \
                            node.scheduler_hints
                        results['nodes'][node.name]['state_list'] = None

                    # try and figure out which baremetal node this
                    # instance is scheduled on
                    if 'bm_node' not in results['nodes'][node.name]:
                        try:
                            bm_node = next(
                                conn.bare_metal.nodes(
                                    details=True, instance_id=node.id))
                            results['nodes'][node.name]['bm_node'] = \
                                bm_node.id
                            results['nodes'][node.name]['bm_node_properties'] = \
                                bm_node.properties
                            results['nodes'][node.name]['bm_node_driver'] = \
                                bm_node.driver
                            results['nodes'][node.name]['bm_last_error'] = \
                                bm_node.last_error
                        except StopIteration:
                            continue

                    update_time = datetime.datetime.strptime(
                        node.updated_at, "%Y-%m-%dT%H:%M:%SZ")
                    results['nodes'][node.name]['last_updated_at'] = \
                        (update_time - start_time).total_seconds()
                    results['nodes'][node.name]['final_status'] = node.status
                    bm_node = next(conn.bare_metal.nodes(details=True,
                                                         instance_id=node.id))
                    state_list = results['nodes'][node.name]['state_list']
                    state_list = \
                        self.state_tracker_extend(bm_node.provision_state,
                                                  state_list)

                    rentry = results['nodes'][node.name]
                    # Populate this field so it gets indexed every time
                    # even if nodes are never pingable
                    rentry['ping_time'] = -1
                    condition = 'private' in node.addresses
                    if condition:
                        ping = self.tools.is_pingable(
                            node.addresses['private'])
                    else:
                        ping = False
                    condition = condition and 'pingable_at' not in rentry
                    condition = condition and ping
                    if condition:
                        ping_time = datetime.datetime.utcnow()
                        rentry['ping_time'] = (
                            ping_time - start_time).total_seconds()

            except exceptions.HttpException:
                self.logger.error("OpenStack bare_metal API is returning NULL")
                self.logger.error(
                    "This sometimes happens during stack creates")
        return results

    def elastic_insert(self, results, run, start_time, benchmark, results_dir):
        scenario_name = benchmark['name']
        results['action'] = scenario_name.strip()
        results['browbeat_rerun'] = run
        results['timestamp'] = str(start_time).replace(" ", "T")
        results['grafana_url'] = self.grafana.grafana_urls()
        results['scenario'] = benchmark['name']
        results['scenario_config'] = benchmark

        # Create list of objects for Elastic insertion rather than
        #  dict of dicts. Insert key to not lose name data
        nodes_data = []
        for key in results['nodes']:
            results['nodes'][key]['name'] = key
            nodes_data.append(results['nodes'][key])
        results['nodes'] = nodes_data

        results = self.elastic.combine_metadata(results)
        if not self.elastic.index_result(results, scenario_name, results_dir):
            self.update_index_failures()

    def dump_scenario_json(self, results_dir, json, time):
        with open(results_dir + "/" + str(time).strip() + ".json", 'w') as outfile:
            outfile.write(json)

    def setup_scenario(self, benchmark_name, dir_ts):
        results_dir = self.tools.create_results_dir(
            results_path, dir_ts, benchmark_name, benchmark_name)

        if isinstance(results_dir, bool):
            self.logger.error(
                "Malformed Config, benchmark names must be unique!")
            exit(1)

        self.logger.debug("Created result directory: {}".format(results_dir))
        self.workload_logger(self.__class__.__name__)
        return results_dir

    def introspection_workload(
            self, benchmark, run, results_dir, env_setup, conn):
        self.delete_stack(conn)
        self.wait_for_clean(env_setup, conn)
        test_start = datetime.datetime.utcnow()

        self.wait_for_clean(env_setup, conn)
        self.set_ironic_node_state("delete", env_setup, conn)
        while len(list(conn.bare_metal.nodes())) > 0:
            time.sleep(5)
        import_results = self.import_instackenv(
            benchmark['instackenv'], env_setup, conn)
        self.set_ironic_node_state("manage", env_setup, conn)
        self.set_ironic_node_state("off", env_setup, conn)

        if benchmark['method'] == "individual":
            introspection_results = self.introspection_individual(
                benchmark['batch_size'], benchmark['timeout'], env_setup, conn)
        elif benchmark['method'] == "bulk":
            introspection_results = self.introspection_bulk(
                benchmark['timeout'], env_setup, conn)
        else:
            self.logger.error(
                "Malformed YODA configuration for " + benchmark['name'])
            exit(1)

        self.get_stats()

        # Combines dicts but mutates import_results rather than
        # returning a new value
        import_results.update(introspection_results)
        results = import_results

        results['total_nodes'] = len(
            list(map(lambda node: node.id, conn.bare_metal.nodes())))
        # If maximum failure precentage is not set, we set it to 10%
        if 'max_fail_amnt' not in benchmark:
            benchmark['max_fail_amnt'] = .10
        if results['failure_count'] >= results['total_nodes'] * \
                benchmark['max_fail_amnt']:
            self.update_fail_tests()
        else:
            self.update_pass_tests()
        self.update_tests()

        self.dump_scenario_json(results_dir, json.dumps(results), test_start)
        if self.config['elasticsearch']['enabled']:
            self.elastic_insert(
                results,
                run,
                test_start,
                benchmark,
                results_dir)

    def overcloud_workload(self, benchmark, run, results_dir, env_setup, conn):
        if conn.orchestration.find_stack("overcloud") is None:
            self.set_ironic_node_state("provide", env_setup, conn)
            self.wait_for_clean(env_setup, conn)

        keep_stack = benchmark['keep_stack']
        results = self.setup_nodes_dict(benchmark)
        changed = True
        while changed:

            changed = False

            # Can't scale from HA to non HA or back
            control_change = results['control'] != results['previous_control']
            if keep_stack and not control_change:
                results['method'] = "update"
            else:
                self.delete_stack(conn)
                self.wait_for_clean(env_setup, conn)
                results['method'] = "new"

            start_time = datetime.datetime.utcnow()
            if 'node_pinning' in benchmark:
                if ostag is None:
                    self.logger.error("ostag is not installed please run")
                    self.logger.error(
                        "   pip install git+https://github.com/jkilpatr/ostag")
                    self.logger.error("Pinning not used in this test!")
                elif benchmark['node_pinning']:
                    ostag.clear_tags(conn)
                    for node in benchmark['cloud']:
                        ostag.mark_nodes(
                            "", node['node'], conn, False, "", node['end_scale'])
                else:
                    ostag.clear_tags(conn)

            results = self.deploy_overcloud(start_time, results,
                                            benchmark['ntp_server'],
                                            conn, env_setup,
                                            benchmark)

            results['total_time'] = (
                datetime.datetime.utcnow() - start_time).total_seconds()
            try:
                stack_status = conn.orchestration.find_stack("overcloud")
            except exceptions.SDKException:
                self.logger.error(
                    "Heat endpoint failed to respond, waiting 10 seconds")
                time.sleep(10)
                continue
            if stack_status is None:
                continue
            results['result'] = str(stack_status.status)
            results['result_reason'] = str(stack_status.status_reason)

            results['total_nodes'] = len(
                list(map(lambda node: node.id, conn.bare_metal.nodes())))
            if "COMPLETE" in results['result']:
                self.update_pass_tests()
            else:
                self.update_fail_tests()
            self.update_tests

            self.get_stats()
            self.tools.gather_metadata()
            self.dump_scenario_json(
                results_dir, json.dumps(results), start_time)
            if self.config['elasticsearch']['enabled']:
                self.elastic_insert(
                    results, run, start_time, benchmark, results_dir)

            out = self.update_nodes_dict(benchmark, results, changed)
            results = out[0]
            changed = out[1]

    def run_workload(self, workload, run_iteration):
        """Iterates through all yoda scenarios in browbeat yaml config file"""
        self.logger.info("Starting YODA workloads")
        es_ts = datetime.datetime.utcnow()
        dir_ts = es_ts.strftime("%Y%m%d-%H%M%S")
        self.logger.debug("Time Stamp (Prefix): {}".format(dir_ts))

        stackrc = self.config.get('yoda')['stackrc']
        env_setup = "env -i bash -c \"source {}; ".format(stackrc)

        auth_vars = self.tools.load_stackrc(stackrc)
        if 'OS_AUTH_URL' not in auth_vars:
            self.logger.error(
                "Please make sure your stackrc is configured correctly")
            exit(1)

        auth_args = {
            'auth_url': auth_vars['OS_AUTH_URL'],
            'project_name': 'admin',
            'username': auth_vars['OS_USERNAME'],
            'password': auth_vars['OS_PASSWORD'],
            'verify': False
        }
        requests.packages.urllib3.disable_warnings()
        conn = connection.Connection(**auth_args)

        instackenv = self.config.get('yoda')['instackenv']

        results_dir = self.setup_scenario(workload['name'], dir_ts)
        times = workload['times']
        if 'instackenv' not in workload:
            workload['instackenv'] = instackenv

        # Correct iteration/rerun
        rerun_range = range(self.config["browbeat"]["rerun"])
        if self.config["browbeat"]["rerun_type"] == "complete":
            rerun_range = range(run_iteration, run_iteration + 1)

        for run in rerun_range:
            for run in range(times):
                if workload['yoda_type'] == "overcloud":
                    self.overcloud_workload(workload, run, results_dir, env_setup, conn)
                elif workload['yoda_type'] == "introspection":
                    self.introspection_workload(workload, run, results_dir, env_setup, conn)
                else:
                    self.logger.error("Could not identify YODA workload!")
                    exit(1)
            self.update_scenarios()

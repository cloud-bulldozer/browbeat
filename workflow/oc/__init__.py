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

import json
import re

DEFAULT_NAMESPACE = "openstack"
DEFAULT_COMMAND = ("ovs-appctl -t /tmp/ovnnb_db.ctl "
                   "cluster/status OVN_Northbound")
DEFAULT_LEADER_PATTERN = "Role: leader"
DEFAULT_POD_LABEL_KEY = "statefulset.kubernetes.io/pod-name"
DEFAULT_TIMEOUT = 120


def get_handlers(workflow_instance):
    """Return OpenShift operation handlers.

    Args:
        workflow_instance: Workflow instance providing tools and logger

    Returns:
        dict: Mapping of operation type strings to handler callables
    """
    return {
        'oc.find_raft_leader': lambda args, step: find_raft_leader(
            workflow_instance, args, step),
    }


def _discover_pods(wf, namespace, pod_prefix, timeout):
    """Discover pods matching a name prefix in the given namespace.

    Args:
        wf: Workflow instance
        namespace (str): OpenShift namespace
        pod_prefix (str): Pod name prefix to filter by
        timeout (int): Command timeout in seconds

    Returns:
        list: Sorted list of pod names matching the prefix
    """
    cmd = ("oc get pods -n {} --no-headers "
           "-o custom-columns=NAME:.metadata.name".format(namespace))

    result = wf.tools.run_cmd(cmd, timeout=timeout)
    if result['rc'] != 0:
        raise Exception(
            "Failed to list pods in namespace {}: {}".format(
                namespace, result['stderr']))

    pods = []
    for line in result['stdout'].splitlines():
        name = line.strip()
        if name.startswith(pod_prefix):
            pods.append(name)

    return sorted(pods)


def _get_pod_labels(wf, pod, namespace, timeout):
    """Fetch labels for a pod as a dictionary.

    Args:
        wf: Workflow instance
        pod (str): Pod name
        namespace (str): OpenShift namespace
        timeout (int): Command timeout in seconds

    Returns:
        dict: Pod labels, or empty dict on failure
    """
    cmd = ("oc get pod {} -n {} "
           "-o jsonpath='{{.metadata.labels}}'".format(pod, namespace))

    result = wf.tools.run_cmd(cmd, timeout=timeout)
    if result['rc'] != 0:
        wf.logger.warning(
            "Could not fetch labels for pod {}: {}".format(
                pod, result['stderr']))
        return {}

    stdout = result['stdout'].strip().strip("'")
    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        wf.logger.warning(
            "Could not parse labels for pod {}".format(pod))
        return {}


def find_raft_leader(wf, args, step):
    """Find the leader pod in a RAFT cluster.

    Discovers pods by prefix, runs a status command on each via oc exec,
    and identifies the leader by matching the output against a pattern.

    Required args:
        pod_prefix (str): Pod name prefix (e.g. 'ovsdbserver-nb')

    Optional args:
        namespace (str): OpenShift namespace (default: openstack)
        container (str): Container name for oc exec -c (default: pod_prefix)
        command (str): Command to check cluster status
        leader_pattern (str): Regex to identify the leader in command output
        pod_label_key (str): Label key for constructing pod_label return value

    Returns:
        dict: Leader info with pod name, labels, and pod_label string
    """
    pod_prefix = args.get('pod_prefix')
    if not pod_prefix:
        raise Exception("'pod_prefix' is required for oc.find_raft_leader")

    namespace = args.get('namespace', DEFAULT_NAMESPACE)
    container = args.get('container', pod_prefix)
    command = args.get('command', DEFAULT_COMMAND)
    leader_pattern = args.get('leader_pattern', DEFAULT_LEADER_PATTERN)
    pod_label_key = args.get('pod_label_key', DEFAULT_POD_LABEL_KEY)
    timeout = step.get('timeout', DEFAULT_TIMEOUT)

    check = wf.tools.run_cmd("which oc")
    if check['rc'] != 0:
        raise Exception("oc is not installed or not in PATH")

    pods = _discover_pods(wf, namespace, pod_prefix, timeout)
    if not pods:
        raise Exception(
            "No pods found matching prefix '{}' in namespace {}".format(
                pod_prefix, namespace))

    wf.logger.info(
        "Discovered {} pods for prefix '{}': {}".format(
            len(pods), pod_prefix, pods))

    leader_pod = None
    leader_output = None

    for pod in pods:
        container_flag = "-c {} ".format(container) if container else ""
        cmd = "oc exec {} -n {} {}-- {}".format(
            pod, namespace, container_flag, command)

        wf.logger.info("Checking RAFT role on pod {}".format(pod))
        wf.logger.debug("Running: {}".format(cmd))

        result = wf.tools.run_cmd(cmd, timeout=timeout)

        if result['rc'] != 0:
            wf.logger.warning(
                "Failed to check pod {} (rc={}): {}".format(
                    pod, result['rc'], result['stderr']))
            continue

        stdout = result['stdout']
        if re.search(leader_pattern, stdout):
            if leader_pod is not None:
                raise Exception(
                    "Multiple leaders found: {} and {}".format(
                        leader_pod, pod))
            leader_pod = pod
            for line in stdout.splitlines():
                if re.search(leader_pattern, line):
                    leader_output = line.strip()
                    break
            wf.logger.info("Found RAFT leader: {}".format(pod))
        else:
            wf.logger.info("Pod {} is not the leader".format(pod))

    if leader_pod is None:
        raise Exception(
            "No RAFT leader found among pods: {}".format(pods))

    labels = _get_pod_labels(wf, leader_pod, namespace, 30)
    pod_label = "{}={}".format(pod_label_key, leader_pod)

    return {
        'pod': leader_pod,
        'namespace': namespace,
        'container': container,
        'pod_label': pod_label,
        'labels': labels,
        'role_output': leader_output,
        'all_pods_checked': pods,
    }

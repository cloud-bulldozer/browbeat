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
import random
import string

DEFAULT_IMAGE_REGISTRY = "quay.io/krkn-chaos/krkn-hub"
DEFAULT_KUBECONFIG = "~/.kube/config"
DEFAULT_TIMEOUT = 600

SCENARIO_IMAGE_TAGS = {
    'pod_scenario': 'pod-scenarios',
    'container_scenario': 'container-scenarios',
    'node_scenario': 'node-scenarios',
    'service_disruption': 'service-disruption-scenarios',
    'power_outage': 'power-outages',
    'pvc_scenario': 'pvc-scenarios',
    'network_chaos': 'network-chaos',
    'time_scenario': 'time-scenarios',
    'zone_outage': 'zone-outages',
    'pod_network_chaos': 'pod-network-chaos'
}


def _generate_container_name(prefix="krkn_"):
    """Generate a unique container name."""
    suffix = ''.join(random.choices(
        string.ascii_lowercase + string.digits, k=8))
    return "{}{}".format(prefix, suffix)


def _build_podman_cmd(args, image, container_name):
    """Build a podman run command string from args.

    Args:
        args (dict): Step arguments containing env, kubeconfig, volumes, etc.
        image (str): Full container image URI with tag
        container_name (str): Name for the container

    Returns:
        str: Complete podman run command
    """
    kubeconfig = os.path.expanduser(
        args.get('kubeconfig', DEFAULT_KUBECONFIG))

    parts = [
        "podman run",
        "--rm",
        "--name={}".format(container_name),
        "--net=host",
        "-v {}:/home/krkn/.kube/config:Z".format(kubeconfig),
    ]

    # Add environment variables
    for key, value in args.get('env', {}).items():
        parts.append("-e {}={}".format(key, str(value)))

    # Add extra volume mounts
    for vol in args.get('volumes', []):
        parts.append("-v {}".format(vol))

    # Add extra podman flags
    for flag in args.get('podman_args', []):
        parts.append(str(flag))

    parts.append(image)

    return " ".join(parts)


def _cleanup_container(wf, container_name):
    """Force remove a container as a safety net."""
    wf.tools.run_cmd("podman rm -f {}".format(container_name))


def get_handlers(workflow_instance):
    """Return krkn-hub chaos operation handlers.

    Args:
        workflow_instance: Workflow instance providing tools and logger

    Returns:
        dict: Mapping of operation type strings to handler callables
    """
    handlers = {
        'krkn.run': lambda args, step: run_scenario(
            workflow_instance, args, step),
    }

    for scenario_type in SCENARIO_IMAGE_TAGS:
        st = scenario_type
        handlers['krkn.{}'.format(st)] = (
            lambda args, step, _st=st: run_typed_scenario(
                workflow_instance, _st, args, step))

    return handlers


def run_scenario(wf, args, step):
    """Run a krkn-hub chaos scenario via podman.

    This is the generic handler for krkn.run. The user must provide
    the full container image URI.

    Required args:
        image (str): Full container image URI (e.g.
            quay.io/krkn-chaos/krkn-hub:pod-scenarios)

    Optional args:
        kubeconfig (str): Path to kubeconfig (default ~/.kube/config)
        env (dict): Environment variables to pass to the container
        volumes (list): Extra volume mounts
        podman_args (list): Extra podman run flags
        container_name (str): Custom container name

    Step-level options:
        timeout (int): Timeout in seconds (default 600)

    Returns:
        dict: Execution result with rc, stdout, stderr, image
    """
    image = args.get('image')
    if not image:
        raise Exception("'image' is required for krkn.run")

    # Check podman is available
    check = wf.tools.run_cmd("which podman")
    if check['rc'] != 0:
        raise Exception("podman is not installed or not in PATH")

    # Validate kubeconfig
    kubeconfig = os.path.expanduser(
        args.get('kubeconfig', DEFAULT_KUBECONFIG))
    if not os.path.isfile(kubeconfig):
        wf.logger.warning(
            "Kubeconfig not found at {}, podman may fail".format(kubeconfig))

    container_name = args.get(
        'container_name', _generate_container_name())
    cmd = _build_podman_cmd(args, image, container_name)

    timeout = step.get('timeout', DEFAULT_TIMEOUT)

    env_keys = list(args.get('env', {}).keys())
    wf.logger.info("Running krkn-hub scenario: image={}, env keys={}".format(
        image, env_keys))
    wf.logger.debug("Full podman command: {}".format(cmd))

    try:
        result = wf.tools.run_cmd(cmd, timeout=timeout)
    except Exception:
        _cleanup_container(wf, container_name)
        raise

    rc = result['rc']
    stdout = result['stdout']
    stderr = result['stderr']

    if isinstance(stderr, bytes):
        stderr = stderr.decode()

    if rc == 0:
        wf.logger.info(
            "krkn-hub scenario completed successfully: {}".format(image))
    elif rc == -1:
        raise Exception(
            "krkn-hub scenario timed out after {} seconds: {}".format(
                timeout, image))
    else:
        raise Exception(
            "krkn-hub scenario failed (rc={}): {}\nstderr: {}".format(
                rc, image, stderr))

    return {
        'rc': rc,
        'stdout': stdout,
        'stderr': stderr,
        'image': image,
        'container_name': container_name,
    }


def run_typed_scenario(wf, scenario_type, args, step):
    """Run a typed krkn-hub scenario (e.g. krkn.pod_scenario).

    Constructs the full image URI from the scenario type and delegates
    to run_scenario.

    Args:
        wf: Workflow instance
        scenario_type (str): Key in SCENARIO_IMAGE_TAGS
        args (dict): Step arguments
        step (dict): Full step definition

    Returns:
        dict: Execution result from run_scenario
    """
    tag = SCENARIO_IMAGE_TAGS[scenario_type]
    registry = args.pop('image_registry', DEFAULT_IMAGE_REGISTRY)
    image = "{}:{}".format(registry, tag)

    args['image'] = image
    return run_scenario(wf, args, step)

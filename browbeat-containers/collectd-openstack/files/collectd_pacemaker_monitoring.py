import collectd
import os

LOG_FILE_PATH = '/var/log/containers/stdouts/collectd_pacemaker.out'
PIPE_FILE_PATH = '/collectd_pipe'
INTERVAL = 15

def config_func(config):
    log_file_path_set = False

    for node in config.children:
        key = node.key.lower()

        if key == 'interval':
            global INTERVAL
            INTERVAL = int(node.values[0])

def read_func():
    global INTERVAL
    global LOG_FILE_PATH

    os.system('''echo "pcs status" > '''+PIPE_FILE_PATH)

    with open(LOG_FILE_PATH, 'rb') as f:
        full_output = f.readlines()

    latest_output = []

    for line in full_output[-1::-1]:
        latest_output.append(line)
        if "Cluster name:" in line:
            break

    components_list = ["total_nodes", "online_nodes", "online_guests",
                       "resource_instances", "haproxy_resource_total_count",
                       "galera_resource_total_count", "rabbitmq_resource_total_count",
                       "redis_resource_total_count", "ovn_resource_total_count", "cinder_resource_total_count",
                       "haproxy_resource_master_count", "galera_resource_master_count", "rabbitmq_resource_master_count",
                       "redis_resource_master_count", "ovn_resource_master_count", "cinder_resource_master_count",
                       "corosync_daemon_status", "pacemaker_daemon_status", "pcsd_daemon_status",
                       "haproxy_resource_failures", "galera_resource_failures", "rabbitmq_resource_failures",
                       "redis_resource_failures", "ovn_resource_failures", "cinder_resource_failures"]

    for component in components_list:
        if component == "total_nodes":
            for line in latest_output[-1::-1]:
                if "nodes configured" in line:
                    line_split = line.split()
                    nodes_index = line_split.index("nodes")
                    val = int(line_split[nodes_index-1])
                    break

        elif component == "online_nodes":
            for line in latest_output[-1::-1]:
                if "Online: [" in line and "Guest" not in line:
                    line_split = line.split("[")[1].replace(" ]","").strip().split()
                    val = int(len(line_split))

        elif component == "online_guests":
            for line in latest_output[-1::-1]:
                if "GuestOnline: [" in line:
                    line_split = line.split("[")[1].replace(" ]","").strip().split()
                    val = int(len(line_split))

        elif component == "resource_instances":
            for line in latest_output[-1::-1]:
                if "resource instances configured" in line:
                    line_split = line.split()
                    nodes_index = line_split.index("resource")
                    val = int(line_split[nodes_index-1])

        elif "resource_total_count" in component:
            resource = component.split("_")[0]
            val = 0
            # Flag to make sure that failures are not counted
            # in resource total count.
            is_failures_total = False
            for line in latest_output[-1::-1]:
                if "Failed" in line:
                    is_failures_total = True
                if (resource == "haproxy" or resource == "galera"
                    or resource == "rabbitmq" or resource == "redis"):
                    if resource+"-bundle-" in line and "Guest" not in line and not is_failures_total:
                        val += 1
                if resource == "ovn":
                    if "ovn-dbs-bundle-" in line and "Guest" not in line and not is_failures_total:
                        val += 1
                if resource == "cinder":
                    if "openstack-cinder-volume-" in line and "Guest" not in line and not is_failures_total:
                        val += 1
                if is_failures_total and "Daemon Status" in line:
                    is_failures_total = False

        elif "resource_master_count" in component:
            resource = component.split("_")[0]
            val = 0
            # Flag to make sure that failures are not counted
            # in resource master count
            is_failures_master = False
            for line in latest_output[-1::-1]:
                if "Failed" in line:
                    is_failures_master = True
                if (resource == "haproxy" or resource == "galera"
                    or resource == "rabbitmq" or resource == "redis"):
                    if resource+"-bundle-" in line and "Master" in line and not is_failures_master:
                        val += 1
                if resource == "ovn":
                    if "ovn-dbs-bundle-" in line and "Master" in line and not is_failures_master:
                        val += 1
                if resource == "cinder":
                    if "openstack-cinder-volume-" in line and "Master" in line and not is_failures_master:
                        val += 1
                if is_failures_master and "Daemon Status" in line:
                    is_failures_master = False

        if "daemon_status" in component:
            daemon = component.split("_")[0]
            val = 0
            for line in latest_output:
                if daemon+":" in line and "active/enabled" in line:
                    val = 1
                    break

        if "resource_failures" in component:
            resource = component.split("_")[0]
            val = 0
            is_failures = False
            for line in latest_output[-1::-1]:
                if "Failed" in line:
                    is_failures = True
                if resource in line and is_failures:
                    val += 1
                if is_failures and "Daemon Status" in line:
                    is_failures = False

        metric = collectd.Values()
        metric.plugin = 'pacemaker_monitoring'
        metric.interval = INTERVAL
        metric.type = 'gauge'
        metric.type_instance = component
        metric.values = [val]
        metric.dispatch()

collectd.register_config(config_func)
collectd.register_read(read_func)

import collectd
import subprocess

INTERVAL = 30

def config_func(config):
    for node in config.children:
        key = node.key.lower()

        if key == 'interval':
            global INTERVAL
            INTERVAL = int(node.values[0])

def read_func():
    global INTERVAL

    nbdb_process = subprocess.Popen(['oc',
                                     'exec',
                                     '-n',
                                     'openstack',
                                     'ovsdbserver-nb-0',
                                     '--',
                                     'ovs-appctl',
                                     '-t',
                                     '/tmp/ovnnb_db.ctl',
                                     'cluster/status',
                                     'OVN_Northbound'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    nbdb_out, nbdb_err = nbdb_process.communicate()
    nbdb_out = nbdb_out.decode("utf-8")

    sbdb_process = subprocess.Popen(['oc',
                                     'exec',
                                     '-n',
                                     'openstack',
                                     'ovsdbserver-sb-0',
                                     '--',
                                     'ovs-appctl',
                                     '-t',
                                     '/tmp/ovnsb_db.ctl',
                                     'cluster/status',
                                     'OVN_Southbound'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    sbdb_out, sbdb_err = sbdb_process.communicate()
    sbdb_out = sbdb_out.decode("utf-8")

    components_list = ["nb_term", "nb_election_timer", "nb_entries_not_committed",
                       "nb_entries_not_applied", "nb_disconnections", "nb_is_leader",
                       "sb_term", "sb_election_timer", "sb_entries_not_committed",
                       "sb_entries_not_applied", "sb_disconnections", "sb_is_leader"]

    for component in components_list:
        val = 0

        if "nb" in component:
            for line in nbdb_out.split("\n"):
                if component == "nb_term" and "Term:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "nb_election_timer" and "Election timer:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "nb_entries_not_committed" and "Entries not yet committed:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "nb_entries_not_applied" and "Entries not yet applied:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "nb_disconnections" and "Disconnections:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "nb_is_leader" and "Role: leader" in line:
                    val = 1
                    break

        elif "sb" in component:
            for line in sbdb_out.split("\n"):
                if component == "sb_term" and "Term:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "sb_election_timer" and "Election timer:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "sb_entries_not_committed" and "Entries not yet committed:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "sb_entries_not_applied" and "Entries not yet applied:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "sb_disconnections" and "Disconnections:" in line:
                    val = int(line.split(": ")[1])
                    break
                elif component == "sb_is_leader" and "Role: leader" in line:
                    val = 1
                    break

        metric = collectd.Values()
        metric.plugin = 'ovn_raft_monitoring'
        metric.interval = INTERVAL
        metric.type = 'gauge'
        metric.type_instance = component
        metric.values = [val]
        metric.dispatch()

collectd.register_config(config_func)
collectd.register_read(read_func)

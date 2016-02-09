#!/usr/bin/env python
import argparse
import yaml
import logging
import sys
sys.path.append('lib/')
from Pbench import *
from Tools import *
from Rally import *
import ConfigParser, os

# Setting up our logger
_logger = logging.getLogger('browbeat')
_logger.setLevel(logging.DEBUG)
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)5s - %(message)s')
_dbg_file = logging.FileHandler('log/debug.log')
_dbg_file.setLevel(logging.DEBUG)
_dbg_file.setFormatter(_formatter)
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(_formatter)
_logger.addHandler(_dbg_file)
_logger.addHandler(_ch)

# import ansible
try :
    from ansible.playbook import PlayBook
    from ansible import callbacks
    from ansible import utils
except ImportError :
    _logger.error("Unable to import Ansible API. This code is not Ansible 2.0 ready")
    exit(1)

# Browbeat specific options
_install_opts=['pbench','connmon','browbeat']
_config_file = 'browbeat-config.yaml'
_config = None

# Load Config file
def _load_config(path):
    stream = open(path, 'r')
    config=yaml.load(stream)
    stream.close()
    return config

# Run Ansible Playbook
def _run_playbook(path, hosts, only_tag=None, skip_tag=None):
    stats = callbacks.AggregateStats()
    playbook_cb = callbacks.PlaybookCallbacks(verbose=1)
    runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=1)
    play = PlayBook(playbook=path,
                    host_list=hosts,
                    stats=stats,
                    only_tags=only_tag,
                    skip_tags=skip_tag,
                    callbacks=playbook_cb,
                    runner_callbacks=runner_cb)
    return play.run()

#
# Browbeat Main
#
if __name__ == '__main__':
    _cli=argparse.ArgumentParser(description="Browbeat automated scrips")
    _cli.add_argument('-n','--hosts',nargs=1,
            help='Provide Ansible hosts file to use. Default is ansible/hosts')
    _cli.add_argument('-s','--setup',nargs=1,
            help='Provide Setup YAML for browbeat. Default is ./browbeat-config.yaml')
    _cli.add_argument('-c','--check',action='store_true',
            help='Run the Browbeat Overcloud Checks')
    _cli.add_argument('-w','--workloads',action='store_true',
            help='Run the Browbeat workloads')
    _cli.add_argument('-i','--install',nargs=1,choices=_install_opts,dest='install',
            help='Install Browbeat Tools')
    _cli.add_argument('--debug',action='store_true',
            help='Enable Debug messages')
    _cli_args = _cli.parse_args()

    if _cli_args.debug :
        _logger.setLevel(logging.DEBUG)

#
# Install Tool(s)
#
    if _cli_args.install :
        if _cli_args.setup :
            _config=_load_config(_cli_args.setup[0])
        else:
            _config=_load_config(_config_file)
        hosts_path=_config['ansible']['hosts']
        if _cli_args.hosts :
            _logger.info("Loading new hosts file : %s"% _cli_args.hosts[0])
            hosts_path=_cli_args.hosts
        if _cli_args.install[0] == 'all' :
            for tool in _install_opts:
                _run_playbook(_config['ansible']['install'][tool],hosts_path)

        elif _cli_args.install[0] in _install_opts :
            _run_playbook(_config['ansible']['install'][_cli_args.install[0]],hosts_path)

#
# Overcloud check
#
    if _cli_args.check :
        if _cli_args.setup :
            _config=_load_config(_cli_args.setup[0])
        else:
            _config=_load_config(_config_file)
        hosts_path=_config['ansible']['hosts']
        if _cli_args.hosts :
            _logger.info("Loading new hosts file : %s"% _cli_args.hosts[0])
            hosts_path=_cli_args.hosts
        _run_playbook(_config['ansible']['check'],hosts_path)

#
# Run Workloads
#
    if _cli_args.workloads :
        hosts = None
        if _cli_args.setup :
            _config=_load_config(_cli_args.setup[0])
        else:
            _config=_load_config(_config_file)
        hosts_path=_config['ansible']['hosts']
        if _config['browbeat']['pbench']['enabled'] :
            pbench_hosts_path=_config['browbeat']['pbench']['hosts']
        if _cli_args.hosts :
            _logger.info("Loading new hosts file : %s"% _cli_args.hosts[0])
            hosts_path=_cli_args.hosts

        if _config['browbeat']['pbench']['enabled'] :
            hosts = ConfigParser.ConfigParser(allow_no_value=True)
            hosts.read(pbench_hosts_path)
        tools = Tools(_config)
        rally = Rally(_config,hosts)
        rally.start_workloads()

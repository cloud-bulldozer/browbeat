#!/usr/bin/env python
from lib.PerfKit import PerfKit
from lib.Rally import Rally
from lib.Shaker import Shaker
import argparse
import logging
import sys
import yaml

_workload_opts = ['perfkit', 'rally', 'shaker']
_config_file = 'browbeat-config.yaml'
debug_log_file = 'log/debug.log'


def _load_config(config_file):
    with open(config_file, 'r') as stream_conf_file:
        config = yaml.load(stream_conf_file)
    return config


def _run_workload_provider(provider, config):
    _logger = logging.getLogger('browbeat')
    if provider == "perfkit":
        perfkit = PerfKit(config)
        perfkit.start_workloads()
    elif provider == "rally":
        rally = Rally(config)
        rally.start_workloads()
    elif provider == "shaker":
        shaker = Shaker(config)
        shaker.run_shaker()
    else:
        _logger.error("Unknown workload provider: {}".format(provider))


def main():
    parser = argparse.ArgumentParser(
        description="Browbeat Performance and Scale testing for Openstack")
    parser.add_argument('-s', '--setup', nargs='?', default=_config_file,
        help='Provide Browbeat YAML configuration file. Default is ./{}'.format(_config_file))
    parser.add_argument('workloads', nargs='*', help='Browbeat workload(s). Takes a space separated'
        ' list of workloads ({}) or \"all\"'.format(', '.join(_workload_opts)))
    parser.add_argument('--debug', action='store_true', help='Enable Debug messages')
    _cli_args = parser.parse_args()

    _logger = logging.getLogger('browbeat')
    _logger.setLevel(logging.DEBUG)
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)7s - %(message)s')
    _dbg_file = logging.FileHandler(debug_log_file)
    _dbg_file.setLevel(logging.DEBUG)
    _dbg_file.setFormatter(_formatter)
    _ch = logging.StreamHandler()
    if _cli_args.debug:
        _ch.setLevel(logging.DEBUG)
    else:
        _ch.setLevel(logging.INFO)
    _ch.setFormatter(_formatter)
    _logger.addHandler(_dbg_file)
    _logger.addHandler(_ch)

    _logger.debug("CLI Args: {}".format(_cli_args))

    # Load Browbeat yaml config file:
    _config = _load_config(_cli_args.setup)

    # Default to all workloads
    if _cli_args.workloads == []:
        _cli_args.workloads.append('all')

    if len(_cli_args.workloads) == 1 and 'all' in _cli_args.workloads:
        _cli_args.workloads = _workload_opts
    invalid_wkld = [wkld for wkld in _cli_args.workloads if wkld not in _workload_opts]
    if invalid_wkld:
        _logger.error("Invalid workload(s) specified: {}".format(invalid_wkld))
        if 'all' in _cli_args.workloads:
            _logger.error("If you meant 'all' use: './browbeat.py all' or './browbeat.py'")
        exit(1)
    else:
        _logger.info("Running workload(s): {}".format(','.join(_cli_args.workloads)))
        for wkld_provider in _cli_args.workloads:
            if wkld_provider in _config:
                if _config[wkld_provider]['enabled']:
                    _run_workload_provider(wkld_provider, _config)
                else:
                    _logger.warning("{} is not enabled in {}".format(wkld_provider,
                        _cli_args.setup))
            else:
                _logger.error("{} is missing in {}".format(wkld_provider, _cli_args.setup))

if __name__ == '__main__':
    sys.exit(main())

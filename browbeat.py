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

from lib.Elastic import browbeat_uuid
from lib import PerfKit
from lib import Rally
from lib import Shaker
from lib import WorkloadBase
import argparse
import logging
import sys
import yaml
import time
import datetime
import os
from pykwalify import core as pykwalify_core
from pykwalify import errors as pykwalify_errors

_workload_opts = ['perfkit', 'rally', 'shaker']
_config_file = 'browbeat-config.yaml'
debug_log_file = 'log/debug.log'

def _load_config(path, _logger):
    try:
        stream = open(path, 'r')
    except IOError:
        _logger.error("Configuration file {} passed is missing".format(path))
        exit(1)
    config = yaml.load(stream)
    stream.close()
    validate_yaml(config, _logger)
    return config

def validate_yaml(config, _logger):
    _logger.info("Validating the configuration file passed by the user")
    stream = open("lib/validate.yaml", 'r')
    schema = yaml.load(stream)
    check = pykwalify_core.Core(source_data=config, schema_data=schema)
    try:
        check.validate(raise_exception=True)
        _logger.info("Validation successful")
    except pykwalify_errors.SchemaError as e:
        _logger.error("Schema Validation failed")
        raise Exception('File does not conform to schema: {}'.format(e))

def _run_workload_provider(provider, config):
    _logger = logging.getLogger('browbeat')
    if provider == "perfkit":
        perfkit = PerfKit.PerfKit(config)
        perfkit.start_workloads()
    elif provider == "rally":
        rally = Rally.Rally(config)
        rally.start_workloads()
    elif provider == "shaker":
        shaker = Shaker.Shaker(config)
        shaker.run_shaker()
    else:
        _logger.error("Unknown workload provider: {}".format(provider))


def main():
    parser = argparse.ArgumentParser(
        description="Browbeat Performance and Scale testing for Openstack")
    parser.add_argument(
        '-s',
        '--setup',
        nargs='?',
        default=_config_file,
        help='Provide Browbeat YAML configuration file. Default is ./{}'.format(_config_file))
    parser.add_argument('workloads', nargs='*', help='Browbeat workload(s). Takes a space separated'
                        ' list of workloads ({}) or \"all\"'.format(', '.join(_workload_opts)))
    parser.add_argument('--debug', action='store_true', help='Enable Debug messages')
    _cli_args = parser.parse_args()

    _logger = logging.getLogger('browbeat')
    _logger.setLevel(logging.DEBUG)
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)7s - %(message)s')
    _formatter.converter = time.gmtime
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
    _config = _load_config(_cli_args.setup, _logger)

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
        time_stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        _logger.info("Browbeat test suite kicked off")
        _logger.info("Browbeat UUID: {}".format(browbeat_uuid))
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
        result_dir = _config['browbeat']['results']
        WorkloadBase.WorkloadBase.print_report(result_dir, time_stamp)
        _logger.info("Saved browbeat result summary to {}".format(
            os.path.join(result_dir,time_stamp + '.' + 'report')))
        WorkloadBase.WorkloadBase.print_summary()
        _logger.info("Browbeat Finished, UUID: {}".format(browbeat_uuid))

if __name__ == '__main__':
    sys.exit(main())

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
import lib.PerfKit
import lib.Rally
import lib.Shaker
import lib.Yoda
import lib.WorkloadBase
import lib.Tools
import argparse
import logging
import sys
import time
import datetime
import os

_workload_opts = ['perfkit', 'rally', 'shaker', 'yoda']
_config_file = 'browbeat-config.yaml'
debug_log_file = 'log/debug.log'

def main():
    tools = lib.Tools.Tools()
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
    parser.add_argument('-p','--postprocess',
                        dest="path",help="Path to process, ie results/20170101/")
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
    _config = tools._load_config(_cli_args.setup)

    # Default to all workloads
    if _cli_args.workloads == []:
        _cli_args.workloads.append('all')
    if _cli_args.path :
        return tools.post_process(_cli_args)

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
        if _config['elasticsearch']['enabled']:
            _logger.info("Checking for Metadata")
            metadata_exists = tools.check_metadata()
            if not metadata_exists:
                _logger.error("Elasticsearch has been enabled but"
                              " metadata files do not exist")
                _logger.info("Gathering Metadata")
                tools.gather_metadata()
            elif _config['elasticsearch']['regather'] :
                _logger.info("Regathering Metadata")
                tools.gather_metadata()

        _logger.info("Running workload(s): {}".format(','.join(_cli_args.workloads)))
        for wkld_provider in _cli_args.workloads:
            if wkld_provider in _config:
                if _config[wkld_provider]['enabled']:
                    tools._run_workload_provider(wkld_provider)
                else:
                    _logger.warning("{} is not enabled in {}".format(wkld_provider,
                                                                     _cli_args.setup))
            else:
                _logger.error("{} is missing in {}".format(wkld_provider, _cli_args.setup))
        result_dir = _config['browbeat']['results']
        lib.WorkloadBase.WorkloadBase.print_report(result_dir, time_stamp)
        _logger.info("Saved browbeat result summary to {}".format(
            os.path.join(result_dir,time_stamp + '.' + 'report')))
        lib.WorkloadBase.WorkloadBase.print_summary()

        browbeat_rc = 0
        if lib.WorkloadBase.WorkloadBase.failure > 0:
            browbeat_rc = 1
        if lib.WorkloadBase.WorkloadBase.index_failures > 0:
            browbeat_rc = 2

        if browbeat_rc == 1:
           _logger.info("Browbeat finished with test failures, UUID: {}".format(browbeat_uuid))
           sys.exit(browbeat_rc)
        elif browbeat_rc == 2:
           _logger.info("Browbeat finished with Elasticsearch indexing failures, UUID: {}"
                        .format(browbeat_uuid))
           sys.exit(browbeat_rc)
        else:
           _logger.info("Browbeat finished successfully, UUID: {}".format(browbeat_uuid))
           sys.exit(0)

if __name__ == '__main__':
    sys.exit(main())

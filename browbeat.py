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

import argparse
import datetime
import logging
import os
import signal
import sys
import time
import browbeat.elastic
import browbeat.tools
import browbeat.workloadbase
from browbeat.config import load_browbeat_config
from browbeat.path import results_path

_workload_opts = ['perfkit', 'rally', 'shaker', 'yoda']
_config_file = 'browbeat-config.yaml'
debug_log_file = 'log/debug.log'

terminate = False

def handle_signal(signum, stack):
    global terminate
    terminate = True


signal.signal(signal.SIGINT, handle_signal)

def run_iteration(_config, _cli_args, result_dir_ts, _logger, tools):
    global terminate
    for workload in _config["workloads"]:
        if not workload["enabled"]:
            _logger.info("{} workload {} disabled in browbeat config".format(workload["type"],
                         workload["name"]))
            continue
        if not workload["type"] in _cli_args.workloads:
            _logger.info("{} workload {} disabled via cli".format(workload["type"],
                         workload["name"]))
            continue
        _logger.info("{} workload {} is enabled".format(workload["type"], workload["name"]))
        tools.run_workload(workload, result_dir_ts, 0)
        browbeat.workloadbase.WorkloadBase.display_summary()
        if terminate:
            return


def run_complete(_config, _cli_args, result_dir_ts, _logger, tools):
    global terminate
    for iteration in range(0, _config["browbeat"]["rerun"]):
        for workload in _config["workloads"]:
            if not workload["enabled"]:
                _logger.info("{} workload {} disabled in browbeat config"
                             .format(workload["type"], workload["name"]))
                continue
            if not workload["type"] in _cli_args.workloads:
                _logger.info("{} workload {} disabled via cli".format(workload["type"],
                             workload["name"]))
                continue
            _logger.info("{} workload {} is enabled".format(workload["type"], workload["name"]))
            tools.run_workload(workload, result_dir_ts, iteration)
            browbeat.workloadbase.WorkloadBase.display_summary()
            if terminate:
                return

def main():
    parser = argparse.ArgumentParser(
        description="Browbeat Performance and Scale testing for Openstack")
    parser.add_argument(
        '-s', '--setup', nargs='?', default=_config_file,
        help='Provide Browbeat YAML configuration file. Default is ./{}'.format(_config_file))
    parser.add_argument(
        'workloads', nargs='*', help='Browbeat workload(s). Takes a space separated'
        ' list of workloads ({}) or \"all\"'.format(', '.join(_workload_opts)))
    parser.add_argument('--debug', action='store_true', help='Enable Debug messages')
    parser.add_argument(
        '-p', '--postprocess', dest="path", help="Path to process, ie results/20171130-191420/")
    parser.add_argument(
        '-c', '--compare', help="Compare metadata", dest="compare", choices=['software-metadata'])
    parser.add_argument(
        '-q', '--query', help="Query Rally Results", dest="query", action='store_true')
    parser.add_argument('-u', '--uuid', help="UUIDs to pass", dest="uuids", nargs=2)
    parser.add_argument('-g', '--get_uuid', help="UUIDs to pass", dest="get_uuids",
                        action='store_true')
    parser.add_argument('--combined', help="Aggregate over times and \
                        concurrency, syntax use --combined <anything>", dest="combined")
    _cli_args = parser.parse_args()

    _logger = logging.getLogger('browbeat')
    _logger.setLevel(logging.DEBUG)
    _formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)7s - %(message)s')
    _formatter.converter = time.gmtime
    _dbg_file = logging.FileHandler(debug_log_file)
    _dbg_file.setLevel(logging.DEBUG)
    _dbg_file.setFormatter(_formatter)
    _ch = logging.StreamHandler(stream=sys.stdout)
    if _cli_args.debug:
        _ch.setLevel(logging.DEBUG)
    else:
        _ch.setLevel(logging.INFO)
    _ch.setFormatter(_formatter)
    _logger.addHandler(_dbg_file)
    _logger.addHandler(_ch)

    _logger.debug("CLI Args: {}".format(_cli_args))

    # Load Browbeat yaml config file:
    _config = load_browbeat_config(_cli_args.setup)
    tools = browbeat.tools.Tools(_config)

    if _cli_args.get_uuids :
        es = browbeat.elastic.Elastic(_config, "BrowbeatCLI")
        data = es.get_results("browbeat-*")
        exit(0)

    # Query Results
    if _cli_args.query :
        es = browbeat.elastic.Elastic(_config, "BrowbeatCLI")
        data,metadata = es.get_result_data("browbeat-rally-*",_cli_args.uuids)
        summary = es.summarize_results(data,bool(_cli_args.combined))
        es.compare_rally_results(summary,_cli_args.uuids,bool(_cli_args.combined),metadata)
        exit(0)

    # Browbeat compare
    if _cli_args.compare == "software-metadata":
        es = browbeat.elastic.Elastic(_config, "BrowbeatCLI")
        es.compare_metadata("browbeat-rally-*", 'controller', _cli_args.uuids)
        exit(0)

    if _cli_args.compare:
        parser.print_help()
        exit(1)

    # Browbeat postprocess
    if _cli_args.path:
        _logger.info("Browbeat Postprocessing {}".format(_cli_args.path))
        return tools.post_process(_cli_args)

    # Browbeat workload - "browbeat run"
    if _cli_args.workloads == []:
        _cli_args.workloads.append('all')

    if len(_cli_args.workloads) == 1 and 'all' in _cli_args.workloads:
        _cli_args.workloads = _workload_opts
    invalid_wkld = [wkld for wkld in _cli_args.workloads if wkld not in _workload_opts]
    if invalid_wkld:
        _logger.error("Invalid workload(s) specified: {}".format(invalid_wkld))
        if 'all' in _cli_args.workloads:
            _logger.error(
                "If you meant 'all' use: './browbeat.py all' or './browbeat.py'")
        exit(1)

    result_dir_ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    _logger.info("Browbeat test suite kicked off")
    _logger.info("Browbeat UUID: {}".format(browbeat.elastic.browbeat_uuid))
    if _config['elasticsearch']['enabled']:
        _logger.info("Checking for Metadata")
        metadata_exists = tools.check_metadata()
        if not metadata_exists:
            _logger.error("Elasticsearch has been enabled but"
                          " metadata files do not exist")
            _logger.info("Gathering Metadata")
            tools.gather_metadata()
        elif _config['elasticsearch']['regather']:
            _logger.info("Regathering Metadata")
            tools.gather_metadata()

    _logger.info("Running workload(s): {}".format(','.join(_cli_args.workloads)))

    # Iteration rerun_type pushes rerun logic down to the workload itself.  This allows the workload
    # to run multiple times before moving to the next workload
    if _config["browbeat"]["rerun_type"] == "iteration":
        run_iteration(_config, _cli_args, result_dir_ts, _logger, tools)
    elif _config["browbeat"]["rerun_type"] == "complete":
        # Complete rerun_type, reruns after all workloads have been run.
        run_complete(_config, _cli_args, result_dir_ts, _logger, tools)
    if terminate:
        _logger.info("Browbeat execution halting due to user intervention")
        sys.exit(1)
    browbeat.workloadbase.WorkloadBase.dump_report(results_path, result_dir_ts)
    _logger.info("Saved browbeat result summary to {}"
                 .format(os.path.join(results_path, "{}.report".format(result_dir_ts))))

    if browbeat.workloadbase.WorkloadBase.failure > 0:
        _logger.info(
            "Browbeat finished with test failures, UUID: {}".format(browbeat.elastic.browbeat_uuid))
        sys.exit(1)

    if browbeat.workloadbase.WorkloadBase.index_failures > 0:
        _logger.info("Browbeat finished with Elasticsearch indexing failures, UUID: {}"
                     .format(browbeat.elastic.browbeat_uuid))
        sys.exit(2)

    _logger.info("Browbeat finished successfully, UUID: {}".format(browbeat.elastic.browbeat_uuid))
    sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())

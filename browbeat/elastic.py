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

from collections import deque
import datetime
import json
import logging
import numpy
import os
import re
import sys
import time
import uuid

import elasticsearch
from elasticsearch import helpers

browbeat_uuid = uuid.uuid4()


class Elastic(object):

    def __init__(
            self,
            config,
            workload,
            tool="browbeat",
            cache_size=1000,
            max_cache_time=10):
        self.config = config
        self.cache = deque()
        self.max_cache_size = cache_size
        self.last_upload = datetime.datetime.utcnow()
        self.max_cache_age = datetime.timedelta(minutes=max_cache_time)
        self.logger = logging.getLogger('browbeat.elastic')
        self.es = elasticsearch.Elasticsearch([
            {'host': self.config['elasticsearch']['host'],
             'port': self.config['elasticsearch']['port']}],
            send_get_body_as='POST'
        )
        self.workload = workload
        today = datetime.datetime.today()
        self.index = "{}-{}-{}".format(tool,
                                       workload, today.strftime('%Y.%m.%d'))

    def __del__(self):
        self.flush_cache()

    def load_json(self, result):
        json_data = None
        self.logger.info("Loading JSON")
        json_data = json.loads(result)
        return json_data

    def load_json_file(self, result):
        json_data = None
        self.logger.info("Loading JSON file : {}".format(result))
        try:
            with open(result) as jdata:
                json_data = json.load(jdata)
        except (IOError, OSError):
            self.logger.error("Error loading JSON file : {}".format(result))
            return False
        return json_data

    def combine_metadata(self, result):
        if (self.config['elasticsearch']['metadata_files'] is not None and
                len(self.config['elasticsearch']['metadata_files']) > 0):
            meta = self.config['elasticsearch']['metadata_files']
            for _meta in meta:
                try:
                    with open(_meta['file']) as jdata:
                        result[_meta['name']] = json.load(jdata)
                except Exception:
                    self.logger.error(
                        "Error loading Metadata file : {}".format(
                            _meta['file']))
                    self.logger.error(
                        "Please make sure the metadata file exists and"
                        " is valid JSON or run the playbook ansible/gather/site.yml"
                        " before running the Browbeat test Suite")
                    sys.exit(1)
        return result

    # Used to transform the cache dict into an elastic insertable iterable
    def cache_insertable_iterable(self):
        output = deque()
        for item in self.cache:
            es_item = {}
            es_item['_id'] = item['_id']
            es_item['_source'] = item['result']
            es_item['_type'] = item['_type']
            es_item['_index'] = self.index
            output.append(es_item)
        return output

    def flush_cache(self):
        if len(self.cache) == 0:
            return True
        retry = 2
        for i in range(retry):
            try:
                to_upload = helpers.parallel_bulk(
                    self.es, self.cache_insertable_iterable())
                counter = 0
                num_items = len(self.cache)
                for item in to_upload:
                    self.logger.debug(
                        "{} of {} Elastic objects uploaded".format(
                            num_items, counter))
                    counter = counter + 1
                output = "Pushed {} items to Elasticsearch to index {}".format(
                    num_items, self.index)
                output += " and browbeat UUID {}".format(str(browbeat_uuid))
                self.logger.info(output)
                self.cache = deque()
                self.last_upload = datetime.datetime.utcnow()
                return True
            except Exception as Err:
                self.logger.error(
                    "Error pushing data to Elasticsearch, going to retry"
                    " in 10 seconds")
                self.logger.error("Exception: {}".format(Err))
                time.sleep(10)
                if i == (retry - 1):
                    self.logger.error(
                        "Pushing Data to Elasticsearch failed in spite of retry,"
                        " dumping JSON for {} cached items".format(
                            len(
                                self.cache)))
                    for item in self.cache:
                        filename = item['test_name'] + '-' + item['identifier']
                        filename += '-elastic' + '.' + 'json'
                        elastic_file = os.path.join(item['result_dir'],
                                                    filename)

                        with open(elastic_file, 'w') as result_file:
                            json.dump(item['result'],
                                      result_file,
                                      indent=4,
                                      sort_keys=True)

                            self.logger.info(
                                "Saved Elasticsearch consumable result JSON to {}". format(
                                    elastic_file))
                    self.cache = deque()
                    self.last_upload = datetime.datetime.utcnow()
                    return False

    def get_software_metadata(self, index, role, browbeat_uuid):
        nodes = {}
        results = self.query_uuid(index, browbeat_uuid)
        pattern = re.compile(".*{}.*".format(role))
        if results:
            for result in results:
                for metadata in result['_source']['software-metadata']:
                    for service in metadata:
                        if pattern.match(metadata[service]['node_name']):
                            if metadata[service]['node_name'] not in nodes:
                                nodes[metadata[service][
                                    'node_name']] = metadata
            return nodes
        else:
            self.logger.error("UUID {} wasn't found".format(browbeat_uuid))
            return False

    """
    summarize_results

    this function will iterate through all the data points, combining the iteration
    and rerun data points into a single 95%tile.
    """

    def summarize_results(self, data, combined):
        summary = {}
        if combined:
            if len(data) > 1:
                for result in data:
                    if result['browbeat_uuid'] not in summary:
                        summary[result['browbeat_uuid']] = {}
                    if result['scenario'] not in summary[result['browbeat_uuid']]:
                        summary[result['browbeat_uuid']][result['scenario']] = {}
                    if result['action'] not in summary[
                            result['browbeat_uuid']][
                            result['scenario']]:
                        summary[result['browbeat_uuid']][
                            result['scenario']][result['action']] = []
                    summary[result['browbeat_uuid']][result['scenario']][
                        result['action']].append(result['performance'])
        else:
            if len(data) > 1:
                for result in data:
                    if result['browbeat_uuid'] not in summary:
                        summary[result['browbeat_uuid']] = {}
                    if result['scenario'] not in summary[result['browbeat_uuid']]:
                        summary[result['browbeat_uuid']][result['scenario']] = {}
                    if result['time'] not in summary[result['browbeat_uuid']][result['scenario']] :
                        summary[result['browbeat_uuid']][result['scenario']][result['time']] = {}
                    if result['concurrency'] not in summary[result['browbeat_uuid']][
                            result['scenario']][result['time']] :
                        summary[result['browbeat_uuid']][result['scenario']][result['time']][
                            result['concurrency']] = {}
                    if result['action'] not in summary[
                            result['browbeat_uuid']][
                            result['scenario']][
                            result['time']][
                            result['concurrency']]:
                        summary[result['browbeat_uuid']][
                            result['scenario']][result['time']][result['concurrency']][
                            result['action']] = []
                    summary[result['browbeat_uuid']][result['scenario']][result['time']][
                        result['concurrency']][
                        result['action']].append(result['performance'])
        if len(summary) > 0 and combined :
            for uuids in summary:
                for scenario in summary[uuids]:
                    for action in summary[uuids][scenario]:
                        summary[uuids][scenario][action] = numpy.percentile(
                            summary[uuids][scenario][action], 95)
        elif len(summary) > 0 and not combined :
            for uuids in summary:
                for scenario in summary[uuids]:
                    for times in summary[uuids][scenario]:
                        for concurrency in summary[uuids][scenario][times]:
                            for action in summary[uuids][scenario][times][concurrency]:
                                summary[uuids][scenario][times][
                                    concurrency][action] = numpy.percentile(
                                    summary[uuids][scenario][times][concurrency][action], 95)
        else:
            return False
        return summary

    """
    """

    def compare_rally_results(self, data, uuids, combined, metadata=None):
        missing = []
        if len(data) < 2:
            self.logger.error("Not enough data to compare")
            return False
        if (uuids[0] not in data) or (uuids[1] not in data):
            self.logger.error("Not able to find UUID in data set")
            return False
        if combined:
            print("+{}+".format("-" * (33 + 44 + 10 + 10 + 23)))
            print("{0:33} | {1:40} | {2:10} | {3:10} | {4:13} ".format("Scenario",
                                                                       "Action",
                                                                       uuids[0][-8:],
                                                                       uuids[1][-8:],
                                                                       "% Difference"))
            print("+{}+".format("-" * (33 + 44 + 10 + 10 + 23)))
            for scenario in data[uuids[0]]:
                if scenario not in data[uuids[1]]:
                    missing.append(scenario)
                    continue
                else:
                    for action in data[uuids[0]][scenario]:
                        dset = [data[uuids[0]][scenario][action],
                                data[uuids[1]][scenario][action]]
                        perf0 = data[uuids[0]][scenario][action]
                        perf1 = data[uuids[1]][scenario][action]
                        diff = numpy.diff(dset)[0] / numpy.abs(dset[:-1])[0] * 100

                        print("{0:33} | {1:40} | {2:10.3f} | {3:10.3f} | {4:13.3f}".format(scenario,
                                                                                           action,
                                                                                           perf0,
                                                                                           perf1,
                                                                                           diff))
            print("+{}+".format("-" * (33 + 44 + 10 + 10 + 26)))
        else:
            print("+{}+".format("-" * (33 + 44 + 15 + 15 + 10 + 10 + 26)))
            print("{0:33} | {1:40} | {2:15} | {3:15} | {4:10} | {5:10} | {6:23}".format(
                  "Scenario",
                  "Action",
                  "times",
                  "concurrency",
                  uuids[0][-8:],
                  uuids[1][-8:],
                  "% Difference"))
            print("+{}+".format("-" * (33 + 44 + 15 + 15 + 10 + 10 + 26)))
            for scenario in data[uuids[0]]:
                if scenario not in data[uuids[1]]:
                    missing.append(scenario)
                    continue
                else:
                    for times in data[uuids[0]][scenario]:
                        if times not in data[uuids[1]][scenario]:
                            continue
                        for concurrency in data[uuids[0]][scenario][times]:
                            if concurrency not in data[uuids[1]][scenario][times]:
                                # Print somehow
                                continue
                            else:
                                for action in data[uuids[0]][scenario][times][concurrency]:
                                    if action not in data[uuids[1]][scenario][times][concurrency]:
                                        # Print somehow
                                        continue
                                    else:
                                        dset = [data[uuids[0]][scenario][times][
                                            concurrency][action],
                                            data[uuids[1]][scenario][times][
                                            concurrency][action]]
                                        perf0 = data[uuids[0]][scenario][times][
                                            concurrency][action]
                                        perf1 = data[uuids[1]][scenario][times][
                                            concurrency][action]
                                        diff = numpy.diff(dset)[0] / numpy.abs(dset[:-1])[0] * 100
                                        output = "{0:33} | {1:40} | {2:15} | {3:15} "
                                        output += "| {4:10.3f} | {5:10.3f} | {6:13.3f}"
                                        print(output.format(scenario,
                                                            action,
                                                            times,
                                                            concurrency,
                                                            perf0,
                                                            perf1,
                                                            diff))
            print("+{}+".format("-" * (33 + 44 + 15 + 15 + 10 + 10 + 26)))
        if metadata:
            print("+{}+".format("-" * (40 + 20 + 20 + 33)))
            print("{0:40} | {1:20} | {2:20} | {3:20}".format("UUID", "Version", "Build",
                                                             "Number of runs"))
            print("+{}+".format("-" * (40 + 20 + 20 + 33)))
            for uuids in metadata:
                print("{0:40} | {1:20} | {2:20} | {3:20}".format(uuids,
                                                                 metadata[uuids][
                                                                     'version'],
                                                                 metadata[uuids][
                                                                     'build'],
                                                                 metadata[uuids]['rerun']))

            print("+{}+".format("-" * (40 + 20 + 20 + 33)))
        if len(missing) > 0:
            print("+-------------------------------------+")
            print("Missing Scenarios to compare results:")
            print("+-------------------------------------+")
            for scenario in missing:
                print(" - {}".format(scenario))

    """
    returns a list of dicts that contain 95%tile performance data.
    """

    def get_result_data(self, index, browbeat_uuid):
        results = []
        data = []
        metadata = {}
        if len(browbeat_uuid) < 1 :
            self.logger.error("No uuids to calculate values")
            return [], {}
        for uuids in browbeat_uuid:
            results.append(self.query_uuid(index, uuids))
        for result in results:
            for value in result:
                if value['_source']['browbeat_uuid'] not in metadata:
                    metadata[value['_source']['browbeat_uuid']] = {}
                    if 'version' in value['_source']:
                        metadata[
                            value['_source']['browbeat_uuid']] = {
                            'version': value['_source']['version']['osp_series'],
                            'build': value['_source']['version']['build'],
                            'rerun': value['_source']['browbeat_config']['browbeat']['rerun']}
                data.append({
                            'browbeat_uuid': value['_source']['browbeat_uuid'],
                            'scenario': value['_source']['scenario'],
                            'action': value['_source']['action'],
                            'time': value['_source']['rally_setup']['kw']['runner']['times'],
                            'concurrency': value['_source']['rally_setup']['kw']['runner'][
                                'concurrency'],
                            'iteration': value['_source']['iteration'],
                            'rerun': value['_source']['browbeat_rerun'],
                            'performance': numpy.percentile(value['_source']['raw'], 95)
                            })
        if len(data) < 1:
            return False
        else:
            return data, metadata

    def get_version_metadata(self, index, browbeat_uuid):
        version = {}
        results = self.query_uuid(index, browbeat_uuid)
        if results:
            for result in results:
                version = result['_source']['version']
            return version
        else:
            self.logger.error("UUID {} wasn't found".format(browbeat_uuid))

    """
    Currently this function will only compare two uuids. I (rook) am not convinced it is worth
    the effort to engineer anything > 2.
    """

    def compare_metadata(self, index, role, uuids):
        meta = []
        for browbeat_uuid in uuids:
            self.logger.info(
                "Querying Elastic : index [{}] : role [{}] : browbeat_uuid [{}] ".format(
                    index, role, browbeat_uuid))
            software_metadata = self.get_software_metadata(
                index, role, browbeat_uuid)
            if software_metadata:
                meta.append(software_metadata)
            else:
                return False

        ignore = [
            "connection",
            "admin_url",
            "bind_host",
            "rabbit_hosts",
            "auth_url",
            "public_bind_host",
            "host",
            "key",
            "url",
            "auth_uri",
            "www_authenticate_uri",
            "coordination_url",
            "swift_authurl",
            "admin_token",
            "memcached_servers",
            "api_servers",
            "osapi_volume_listen",
            "nova_url",
            "coordination_url",
            "memcache_servers",
            "novncproxy_host",
            "backend_url",
            "novncproxy_base_url",
            "metadata_listen",
            "osapi_compute_listen",
            "admin_bind_host",
            "glance_api_servers",
            "iscsi_ip_address",
            "registry_host",
            "auth_address",
            "swift_key",
            "auth_encryption_key",
            "metadata_proxy_shared_secret",
            "telemetry_secret",
            "heat_metadata_server_url",
            "heat_waitcondition_server_url",
            "catalog_info",
            "gather_conf_path",
            "exec_dirs",
            "transport_url"]
        if len(meta) < 2:
            self.logger.error("Unable to compare data-sets")
            return False

        differences = []
        for host in meta[0]:
            if host not in meta[1]:
                self.logger.error("Deployment differs: "
                                  "Host [{}] missing ".format(host))
                continue
            for service in meta[0][host]:
                for options in meta[0][host][service].keys():
                    if options not in meta[1][host][service]:
                        self.logger.debug(
                            "UUID {} "
                            "- Missing Option : "
                            "Host [{}] Service [{}] {}".format(
                                uuids[1], host, service, options))
                        continue
                    if isinstance(meta[0][host][service][options], dict):
                        for key in meta[0][host][service][options].keys():
                            if key not in ignore:
                                if key in meta[1][host][service][options]:
                                    value = meta[0][host][
                                        service][options][key]
                                    new_value = meta[1][host][
                                        service][options][key]
                                    if value != new_value:
                                        differences.append("{}|{}|{}|{}|{}|{}".format(
                                            host,
                                            service,
                                            options,
                                            key,
                                            value,
                                            new_value))
                                else:
                                    self.logger.error(
                                        "UUID {} - Missing Value : "
                                        "Host [{}] Service [{}] {} [{}]".format(
                                            uuids[1], host, service, options, key))

        print("+{}+".format("-" * (33 + 44 + 15 + 15 + 30 + 10 + 6)))
        print("{0:25} | {1:15} | {2:30} | {3:23} | {4:40} | {5:40} ".format(
              "Host",
              "Service",
              "Option",
              "Key",
              "Old Value",
              "New Value"))
        print("+{}+".format("-" * (33 + 44 + 15 + 15 + 30 + 10 + 6)))
        for difference in differences:
            value = difference.split("|")
            print("{0:25} | {1:15} | {2:30} | {3:23} | {4:40} | {5:40} ".format(value[0],
                                                                                value[1],
                                                                                value[2],
                                                                                value[3],
                                                                                value[4],
                                                                                value[5]))
        print("+{}+".format("-" * (33 + 44 + 15 + 15 + 30 + 10 + 6)))

    def scroll(self, search, sid, scroll_size):
        data = []
        if scroll_size < 1 :
            self.logger.info("Nothing to sroll through")
            return data
        while (scroll_size > 0):
            self.logger.info("Scrolling through Browbeat {} documents...".format(scroll_size))
            for x in range(0, len(search['hits']['hits'])) :
                data.append(search['hits']['hits'][x])
            search = self.es.scroll(scroll_id=sid, scroll='2m')
            sid = search['_scroll_id']
            scroll_size = len(search['hits']['hits'])
        return data

    """
    get_errors - was inteded to capture all the errors across the entire
    index, however, this is quite expensive, and it might be quicker to
    only look for errors for specific browbeat_uuids
    """

    def get_errors(self, index, browbeat_id):
        self.logger.info("Making query against {}".format(index))
        page = self.es.search(
            index=index,
            doc_type='error',
            scroll='2m',
            size=5000,
            body={"query": {"browbeat_uuid": browbeat_id}})
        sid = page['_scroll_id']
        scroll_size = page['hits']['total']
        return self.scroll(sid,scroll_size)

    def get_results(self, index, browbeat_uuid):
        body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "term": {
                                "browbeat_uuid": browbeat_uuid
                                }}]}}}
        self.logger.info("Making query against {}".format(index))
        page = self.es.search(
            index=index,
            doc_type='result',
            scroll='1m',
            size=1000,
            body=body,
            request_timeout=240)
        sid = page['_scroll_id']
        scroll_size = page['hits']['total']
        self.logger.info("Searching through ES for uuid: {}".format(browbeat_uuid))
        return self.scroll(page,sid,scroll_size)

    def query_uuid(self, index, browbeat_uuid):
        results = self.get_results(index, browbeat_uuid)
        if len(results) > 0:
            return results
        else:
            self.logger.info("No results found for uuid : {}".format(browbeat_uuid))
            return False

    def index_result(self,
                     result,
                     test_name,
                     result_dir,
                     identifier='',
                     _type='result',
                     _id=None):
        data = {}
        result['browbeat_uuid'] = str(browbeat_uuid)
        result['cloud_name'] = self.config['browbeat']['cloud_name']
        result['browbeat_config'] = self.config
        data['result'] = result
        data['test_name'] = test_name
        data['result_dir'] = result_dir
        data['identifier'] = identifier
        data['_type'] = _type
        data['_id'] = _id
        self.cache.append(data)
        now = datetime.datetime.utcnow()
        if (len(self.cache) <= self.max_cache_size and
                (now - self.last_upload) <= self.max_cache_age):
            return True
        else:
            return self.flush_cache()

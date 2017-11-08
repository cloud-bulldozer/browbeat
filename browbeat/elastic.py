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
import os
import re
import sys
import time
import uuid

import elasticsearch
from elasticsearch import helpers

browbeat_uuid = uuid.uuid4()


class Elastic(object):

    def __init__(self, config, workload, tool="browbeat", cache_size=1000, max_cache_time=10):
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

    # Used to transform the cache dict into a elastic insertable iterable
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
                to_upload = helpers.parallel_bulk(self.es,
                                                  self.cache_insertable_iterable())
                counter = 0
                num_items = len(self.cache)
                for item in to_upload:
                    self.logger.debug("{} of {} Elastic objects uploaded".format(num_items,
                                                                                 counter))
                    counter = counter + 1
                output = "Pushed {} items to Elasticsearch to index {}".format(num_items,
                                                                               self.index)
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
                    self.logger.error("Pushing Data to Elasticsearch failed in spite of retry,"
                                      " dumping JSON for {} cached items".format(len(self.cache)))
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

                            self.logger.info("Saved Elasticsearch consumable result JSON to {}".
                                             format(elastic_file))
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

            version_metadata = self.get_version_metadata(index, browbeat_uuid)
            if version_metadata:
                self.logger.info(
                    "\nUUID: {}\nVersion: {}\nBuild: {}".format(
                        browbeat_uuid,
                        version_metadata['osp_series'],
                        version_metadata['build']))

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
            "transport_url"]
        if len(meta) < 2:
            self.logger.error("Unable to compare data-sets")
            return False
        for host in meta[0]:
            if host not in meta[1]:
                self.logger.error("Deployment differs: "
                                  "Host [{}] missing ".format(host))
                continue
            for service in meta[0][host]:
                for options in meta[0][host][service].keys():
                    if options not in meta[1][host][service]:
                        self.logger.error(
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
                                        self.logger.info(
                                            "Difference found : "
                                            "Host [{}] Service [{}] Section {} {} [{}]\n"
                                            "New Value: {}\nOld Value: {}".format(
                                                host,
                                                service,
                                                options,
                                                key,
                                                meta[0][host][service][
                                                    options][key],
                                                value,
                                                new_value))
                                else:
                                    self.logger.error(
                                        "UUID {} - Missing Value : "
                                        "Host [{}] Service [{}] {} [{}]".format(
                                            uuids[1], host, service, options, key))

    def query_uuid(self, index, browbeat_uuid):
        body = {'query': {"match": {"browbeat_uuid": {
            "query": browbeat_uuid, "type": "phrase"}}}}
        results = self.es.search(index=index, doc_type='result', body=body)
        if len(results['hits']['hits']) > 0:
            return results['hits']['hits']
        else:
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

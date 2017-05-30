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

import elasticsearch
import logging
import json
import datetime
import uuid
import sys
import time
import os

browbeat_uuid = uuid.uuid4()


class Elastic(object):

    def __init__(self, config, workload, tool="browbeat"):
        self.config = config
        self.logger = logging.getLogger('browbeat.Elastic')
        self.es = elasticsearch.Elasticsearch([
            {'host': self.config['elasticsearch']['host'],
             'port': self.config['elasticsearch']['port']}],
            send_get_body_as='POST'
        )
        self.workload = workload
        today = datetime.datetime.today()
        self.index = "{}-{}-{}".format(tool, workload, today.strftime('%Y.%m.%d'))

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
                        "Error loading Metadata file : {}".format(_meta['file']))
                    self.logger.error("Please make sure the metadata file exists and"
                                      " is valid JSON or run the playbook ansible/gather/site.yml"
                                      " before running the Browbeat test Suite")
                    sys.exit(1)
        return result

    def index_result(self, result, test_name, result_dir, identifier='', _type='result',
                     _id=None):
        retry = 2
        result['browbeat_uuid'] = str(browbeat_uuid)
        result['cloud_name'] = self.config['browbeat']['cloud_name']
        result['browbeat_config'] = self.config
        for i in range(retry):
            try:
                self.es.index(index=self.index,
                              id=_id,
                              body=result,
                              doc_type=_type,
                              refresh=True)
                self.logger.debug("Pushed data to Elasticsearch to index {}"
                                  "and browbeat UUID {}".
                                  format(self.index, result['browbeat_uuid']))
                return True
            except Exception as Err:
                self.logger.error("Error pushing data to Elasticsearch, going to retry"
                                  " in 10 seconds")
                self.logger.error("Exception: {}".format(Err))
                time.sleep(10)
                if i == (retry-1):
                        self.logger.error("Pushing Data to Elasticsearch failed in spite of retry,"
                                          " dumping JSON")
                        elastic_file = os.path.join(result_dir,
                                                    test_name + '-' + identifier + '-elastic' +
                                                    '.' + 'json')
                        with open(elastic_file, 'w') as result_file:
                            json.dump(result, result_file, indent=4, sort_keys=True)
                            self.logger.info("Saved Elasticsearch consumable result JSON to {}".
                                             format(elastic_file))
                        return False

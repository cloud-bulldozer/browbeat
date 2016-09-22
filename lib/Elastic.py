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

browbeat_uuid = uuid.uuid4()


class Elastic(object):

    """
    """

    def __init__(self, config, workload, tool="browbeat"):
        self.config = config
        self.logger = logging.getLogger('browbeat.Elastic')
        self.es = elasticsearch.Elasticsearch([
            {'host': self.config['elasticsearch']['host'],
             'port': self.config['elasticsearch']['port']}],
            send_get_body_as='POST'
        )
        today = datetime.datetime.today()
        self.index = "{}-{}-{}".format(tool, workload, today.strftime('%Y.%m.%d'))

    """
    """

    def load_json(self, result):
        json_data = None
        self.logger.info("Loading JSON")
        json_data = json.loads(result)
        return json_data

    """
    """

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

    """
    """

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

    """
    """

    def index_result(self, result, _type='result', _id=None):
        result['browbeat_uuid'] = browbeat_uuid
        result['cloud_name'] = self.config['browbeat']['cloud_name']
        return self.es.index(index=self.index,
                             id=_id,
                             body=result,
                             doc_type=_type,
                             refresh=True
                             )

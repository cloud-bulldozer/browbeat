from elasticsearch import Elasticsearch
import logging
import json
import pprint
import numpy
import datetime

class Elastic:
    """
    """
    def __init__(self,config,tool="browbeat") :
        self.config = config
        self.logger = logging.getLogger('browbeat.Elastic')
        self.es = Elasticsearch([
            {'host': self.config['elasticsearch']['host'],
             'port': self.config['elasticsearch']['port']}],
            send_get_body_as='POST'
        )
        today = datetime.datetime.today()
        self.index = "{}-{}".format(tool,today.strftime('%Y.%m.%d'))

    """
    """
    def load_json(self,result):
        json_data = None
        self.logger.info("Loading JSON")
        json_data = json.loads(result)
        return json_data

    """
    """
    def load_json_file(self,result):
        json_data = None
        self.logger.info("Loading JSON file : {}".format(result))
        try :
            with open(result) as jdata :
                json_data = json.load(jdata)
        except (IOError, OSError) as e:
            self.logger.error("Error loading JSON file : {}".format(result))
            return False
        return json_data

    """
    """
    def combine_metadata(self,result):
        if len(self.config['elasticsearch']['metadata_files']) > 0 :
            meta = self.config['elasticsearch']['metadata_files']
            for _meta in meta:
                try :
                    with open(_meta['file']) as jdata :
                        result[_meta['name']] = json.load(jdata)
                except (IOError, OSError) as e:
                    self.logger.error("Error loading Metadata file : {}".format(_meta['file']))
                    return False
            return result

    """
    """
    def index_result(self,result,_type='result',_id=None) :
        return self.es.index(index=self.index,
                             id=_id,
                             body=result,
                             doc_type=_type,
                             refresh=True
                             )

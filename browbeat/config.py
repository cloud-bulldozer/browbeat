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

import logging
import yaml

from pykwalify import core as pykwalify_core
from pykwalify import errors as pykwalify_errors

from browbeat.path import conf_schema_path


_logger = logging.getLogger("browbeat.config")

def load_browbeat_config(path):
    """Loads and validates an entire Browbeat config per the expected schema.

    :param path: The path to the Browbeat Config file
    """
    with open(path, "r") as config_file:
        browbeat_config = yaml.safe_load(config_file)
    _logger.debug("Browbeat config {} yaml loaded".format(path))

    # Validate base config for Browbeat format
    _validate_yaml("browbeat", browbeat_config)
    _logger.info("Config {} validated".format(path))

    # Validate per-workloads
    for workload in browbeat_config["workloads"]:
        _validate_yaml(workload["type"], workload)
        _logger.debug("Workload {} validated as {}".format(workload["name"], workload["type"]))

    return browbeat_config

def _validate_yaml(schema, config):
    """Raises exception if config is invalid.

    :param schema: The schema to validate with (browbeat, perfkit, rally...)
    :param config: Loaded yaml to validate
    """
    check = pykwalify_core.Core(
        source_data=config, schema_files=["{}/{}.yml".format(conf_schema_path, schema)])
    try:
        check.validate(raise_exception=True)
    except pykwalify_errors.SchemaError as e:
        _logger.error("Schema validation failed")
        raise Exception("File does not conform to {} schema: {}".format(schema, e))

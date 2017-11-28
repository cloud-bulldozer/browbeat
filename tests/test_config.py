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

import pytest
import yaml

from browbeat.config import load_browbeat_config
from browbeat.config import _validate_yaml

test_browbeat_configs = {
    "tests/data/valid_browbeat.yml": True,
    "tests/data/invalid_browbeat.yml": False,
    "tests/data/invalid_browbeat_workload.yml": False
}


@pytest.mark.parametrize("config", test_browbeat_configs.keys())
def test_load_browbeat_config(config):
    """Tests valid and invalid Browbeat configuration."""
    if test_browbeat_configs[config]:
        # Valid configuration (No exception)
        loaded_config = load_browbeat_config(config)
        assert loaded_config["browbeat"]["cloud_name"] == "browbeat-test"
    else:
        # Invalid configuration, test for exception
        with pytest.raises(Exception) as exception_data:
            load_browbeat_config(config)
        assert "SchemaError" in str(exception_data)


@pytest.mark.parametrize("schema", ["perfkit", "rally", "shaker", "yoda"])
def test__validate_yaml(schema):
    """Tests valid and invalid Browbeat workload configurations."""
    with open("tests/data/workloads.yml", "r") as config_file:
        config_data = yaml.safe_load(config_file)

    for workload_config in config_data[schema]:
        if workload_config["valid"]:
            # Valid configuration (No exception)
            _validate_yaml(schema, workload_config["data"])
        else:
            # Invalid configuration, test for exception
            with pytest.raises(Exception) as exception_data:
                _validate_yaml(schema, workload_config["data"])
            assert "SchemaError" in str(exception_data)

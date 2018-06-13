#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from rally.common import logging
from rally_openstack import consts
from rally_openstack.context.network import networks
from rally.task import context

LOG = logging.getLogger(__name__)


@context.configure(name="browbeat_persist_network", order=350)
class BrowbeatPersistNetwork(networks.Network):
    """Create networking resources but does not clean them up
    at the conclusion to allow resources to persist.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "start_cidr": {
                "type": "string"
            },
            "networks_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
            "subnets_per_network": {
                "type": "integer",
                "minimum": 1
            },
            "network_create_args": {
                "type": "object",
                "additionalProperties": True
            },
            "dns_nameservers": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True
            }
        },
        "additionalProperties": True
    }

    def setup(self):
        super(BrowbeatPersistNetwork, self).setup()

    def cleanup(self):
        pass

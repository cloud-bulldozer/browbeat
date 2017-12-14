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

import time

from rally.common import logging
from rally.task import context
from rally import consts


LOG = logging.getLogger(__name__)


@context.configure(name="browbeat_delay", order=400)
class BrowbeatDelay(context.Context):
    """Add delay to start or end of a rally scenario."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "setup_delay": {
                "type": "integer",
                "minimum": 0
            },
            "cleanup_delay": {
                "type": "integer",
                "minimum": 0
            },
        },
        "additionalProperties": False
    }

    def setup(self):
        if self.config.get('setup_delay'):
            LOG.info('Setup Delaying: {}'.format(self.config.get('setup_delay')))
            time.sleep(self.config.get('setup_delay'))

    def cleanup(self):
        if self.config.get('cleanup_delay'):
            LOG.info('Cleanup Delaying: {}'.format(self.config.get('cleanup_delay')))
            time.sleep(self.config.get('cleanup_delay'))

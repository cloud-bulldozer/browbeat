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

from workflow.nova import get_handlers as get_nova_handlers
from workflow.neutron import get_handlers as get_neutron_handlers
from workflow.common import get_handlers as get_common_handlers
from workflow.krkn import get_handlers as get_krkn_handlers
from workflow.oc import get_handlers as get_oc_handlers


def get_all_handlers(workflow_instance):
    """Return combined handler map from all project modules.

    Args:
        workflow_instance: Workflow instance providing os_clients, logger, state

    Returns:
        dict: Mapping of operation type strings to handler callables
    """
    handlers = {}
    handlers.update(get_nova_handlers(workflow_instance))
    handlers.update(get_neutron_handlers(workflow_instance))
    handlers.update(get_common_handlers(workflow_instance))
    handlers.update(get_krkn_handlers(workflow_instance))
    handlers.update(get_oc_handlers(workflow_instance))
    return handlers

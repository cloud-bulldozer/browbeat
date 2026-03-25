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

import time


def get_handlers(workflow_instance):
    """Return common workflow operation handlers.

    Args:
        workflow_instance: Workflow instance providing logger

    Returns:
        dict: Mapping of operation type strings to handler callables
    """
    return {
        'workflow.wait': lambda args, step: wait(workflow_instance, args, step),
        'workflow.log': lambda args, step: log(workflow_instance, args, step),
    }


def wait(wf, args, step):
    """Sleep for specified seconds.

    Args:
        wf: Workflow instance
        args (dict): Arguments with 'seconds' key
        step (dict): Full step definition

    Returns:
        dict: Wait information
    """
    seconds = args.get('seconds', 1)
    wf.logger.info("Waiting for {} seconds".format(seconds))
    time.sleep(seconds)

    return {'seconds': seconds}


def log(wf, args, step):
    """Log a message.

    Args:
        wf: Workflow instance
        args (dict): Arguments with 'message' key
        step (dict): Full step definition

    Returns:
        dict: Log information
    """
    message = args.get('message', '')
    level = args.get('level', 'info').lower()

    if level == 'debug':
        wf.logger.debug(message)
    elif level == 'warning':
        wf.logger.warning(message)
    elif level == 'error':
        wf.logger.error(message)
    else:
        wf.logger.info(message)

    return {'message': message, 'level': level}

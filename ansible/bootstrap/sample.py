#!/usr/bin/env python
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
import time

LOG = logging.getLogger("browbeat.sample")


def register(installer_types, subparser):
    installer_types["sample"] = sample
    sample_parser = subparser.add_parser("sample")
    sample_parser.add_argument("-s", "--sample-arg")


class sample(object):

    def bootstrap(self, working_dir, cliargs):
        """Sample bootstrap installer."""
        start_time = time.time()
        LOG.info("Bootstrap via sample installer")

        # Insert code to generate ssh-config and hosts files for Ansible
        LOG.info("This is provided as a sample to copy and paste to make a new installer plugin.")

        LOG.info("Completed bootstrap in {}".format(round(time.time() - start_time, 2)))

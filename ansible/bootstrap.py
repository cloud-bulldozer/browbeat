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

import argparse
import datetime
import logging
import os
import sys
import time

installer_types = {}


def main(args):
    working_dir = os.path.dirname(os.path.realpath(__file__))

    parser = argparse.ArgumentParser(
        description="Browbeat bootstrap Ansible. Generates files for Ansible interactions to the "
                    "OpenStack Cloud.", prog="bootstrap.py")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable Debug messages")
    subparsers = parser.add_subparsers(dest="installer")

    # Load pluggable installers
    pluggable_installers_dir = os.path.join(working_dir, "bootstrap")
    installer_plugins = [x[:-3] for x in os.listdir(pluggable_installers_dir) if x.endswith(".py")]
    sys.path.insert(0, pluggable_installers_dir)
    for installer in sorted(installer_plugins):
        installer_mod = __import__(installer)
        if hasattr(installer_mod, "register"):
            installer_mod.register(installer_types, subparsers)

    cliargs = parser.parse_args(args)

    LOG = logging.getLogger("browbeat")
    LOG.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    formatter.converter = time.gmtime
    handler = logging.StreamHandler(stream=sys.stdout)
    if cliargs.debug:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    LOG.addHandler(handler)

    LOG.debug("CLI Args: {}".format(cliargs))

    installer_types[cliargs.installer]().bootstrap(working_dir, cliargs)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

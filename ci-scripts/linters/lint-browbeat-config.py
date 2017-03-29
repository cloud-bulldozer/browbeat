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

import yaml
import sys
from pykwalify import core as pykwalify_core
from pykwalify import errors as pykwalify_errors
stream = open(sys.argv[1], 'r')
schema = yaml.load(stream)
check = pykwalify_core.Core(sys.argv[2], schema_data=schema)
try:
    check.validate(raise_exception=True)
    print ("Validation successful")
    exit(0)
except pykwalify_errors.SchemaError as e:
    print ("Config " + sys.argv[2] + " is not valid!")
    raise Exception('File does not conform to schema: {}'.format(e))

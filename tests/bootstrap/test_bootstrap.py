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

import os
import sys
import pytest
sys.path.append(os.path.abspath('ansible'))
import bootstrap  # noqa


def test_bootstrap_help(capsys):
    """Tests to see if bootstrap.py help text is correct and that it loads sample/tripleo plugins"""
    help_text = ("usage: bootstrap.py [-h] [-d] {sample,tripleo} ...\n\n"
                 "Browbeat bootstrap Ansible. Generates files for Ansible interactions to the\n"
                 "OpenStack Cloud.\n\n"
                 "positional arguments:\n"
                 "  {sample,tripleo}\n\n"
                 "optional arguments:\n"
                 "  -h, --help        show this help message and exit\n"
                 "  -d, --debug       Enable Debug messages\n")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        bootstrap.main(["-h",])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    out, err = capsys.readouterr()
    assert out == help_text

def test_bootstrap_tripleo_help(capsys):
    """Tests to see if bootstrap.py tripleo plugin help text is correct."""
    help_text = ("usage: bootstrap.py tripleo [-h] [-i TRIPLEO_IP] [-u USER]\n\n"
                 "Bootstrap implementation for tripleo clouds\n\n"
                 "optional arguments:\n"
                 "  -h, --help            show this help message and exit\n"
                 "  -i TRIPLEO_IP, --tripleo-ip TRIPLEO_IP\n"
                 "                        IP address of tripleo undercloud. Defaults to\n"
                 "                        'localhost'. Currently only localhost is supported.\n"
                 "  -u USER, --user USER  User used for tripleo install. Defaults to 'stack'.\n")

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        bootstrap.main(["tripleo", "-h"])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
    out, err = capsys.readouterr()
    assert out == help_text

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

from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import validation


class KeystonePlugin(scenario.OpenStackScenario):
    @validation.number("repetitions", minval=1)
    @validation.required_openstack(users=True)
    @scenario.configure()
    def validate_ceilometer(self, repetitions):
        """Check Ceilometer Client to ensure validation of token.
        Creation of the client does not ensure validation of the token.
        We have to do some minimal operation to make sure token gets validated.
        :param repetitions: number of times to validate
        """
        ceilometer_client = self.clients("ceilometer")
        with atomic.ActionTimer(self, "authenticate.validate_ceilometer_%s_times" %
                                repetitions):
            for i in range(repetitions):
                ceilometer_client.meters.list()

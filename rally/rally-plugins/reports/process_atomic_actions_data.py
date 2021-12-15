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

class AtomicActionsDurationDataProcessor:
    """Generate charts for atomic actions durations additive and complete data"""

    def __init__(self):
        self._duration_data = {}
        self.max_num_data_points = 0

    def process_atomic_actions_complete_data(self, atomic_actions):
        """Generate duration data in complete format for per iteration chart
        :param atomic_actions: list, self.atomic_actions() from a rally scenario
        """
        for action in atomic_actions:
            if action["name"] not in self._duration_data:
                self._duration_data[action["name"]] = []
            action_duration = action["finished_at"] - action["started_at"]
            self._duration_data[action["name"]].append([len(self._duration_data[action["name"]]),
                                                       action_duration])
            self.max_num_data_points = max(self.max_num_data_points,
                                           len(self._duration_data[action["name"]]))

    def get_duplicate_actions_list(self, atomic_actions):
        """Get list of atomic actions which occur more than once in an iteration
        :param atomic_actions: list, self.atomic_actions() from a rally scenario
        :returns: list of strings representing duplicate action names
        """
        actions_set = set()
        duplicate_actions_set = set()
        for action in atomic_actions:
            if action["name"] not in actions_set:
                actions_set.add(action["name"])
            else:
                duplicate_actions_set.add(action["name"])
        return list(duplicate_actions_set)

    def process_atomic_action_additive_data(self, action_name, atomic_actions):
        """Generate duration data in additive format for aggregate chart
        :param action_name: str, action name to generate duration data for
        :param atomic_actions: list, self.atomic_actions() from a rally scenario
        :returns: list in Rally additive data format
        """
        additive_duration_data = []
        action_index = 1
        for action in atomic_actions:
            if action["name"] == action_name:
                additive_duration_data.append(["{}({})".format(action_name, action_index),
                                               action["finished_at"] - action["started_at"]])
                action_index += 1
        return additive_duration_data

    def zeropad_duration_data(self):
        """Some atomic actions occur more times than other atomic actions
        within the same iteration. Zeroes are appended to make the length
        of all atomic action lists the same
        """
        for action_name in self._duration_data:
            while len(self._duration_data[action_name]) < self.max_num_data_points:
                self._duration_data[action_name].append([len(self._duration_data[action_name]), 0])

    def get_complete_duration_data(self):
        """Complete duration data is stored in dict format to increase efficiency
        of operations. Rally add_output() function expects a list as input. This
        function converts the complete duration data to the format expected by the
        Rally add_output() function.
        """
        return [[name, durations] for name, durations in self._duration_data.items()]

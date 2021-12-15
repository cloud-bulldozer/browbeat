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

from process_atomic_actions_data import AtomicActionsDurationDataProcessor

class ScenarioDurationChartsGenerator(AtomicActionsDurationDataProcessor):
    """Send processed complete and additive atomic action duration data to Rally"""

    def add_per_iteration_complete_data(self, scenario_object):
        """Generate a stacked area graph for duration trend for each atomic action
        in an iteration.
        :param scenario_object: Rally scenario object
        """
        atomic_actions = scenario_object.atomic_actions()
        self.process_atomic_actions_complete_data(atomic_actions)
        # Some actions might have been executed more times than other actions
        # in the same iteration. Zeroes are appended to make the numbers equal.
        self.zeropad_duration_data()
        scenario_object.add_output(complete={
                                   "title": "Atomic actions duration data as stacked area",
                                   "description": "Iterations trend",
                                   "chart_plugin": "StackedArea",
                                   "data": (
                                       self.get_complete_duration_data()),
                                   "label": "Duration(in seconds)",
                                   "axis_label": "Atomic action"})

    def add_duplicate_atomic_actions_iteration_additive_data(self, scenario_object):
        """Generate line graphs for atomic actions that have been executed more than once
        in the same iteration.
        :param scenario_object: Rally scenario object
        """
        atomic_actions = scenario_object.atomic_actions()
        for action_name in self.get_duplicate_actions_list(atomic_actions):
            additive_data_duplicate_action = (
                self.process_atomic_action_additive_data(action_name,
                                                         atomic_actions))
            scenario_object.add_output(additive={
                                       "title": "{} additive duration data as line chart".format(
                                                action_name),
                                       "description": "Iterations trend",
                                       "chart_plugin": "Lines",
                                       "data": additive_data_duplicate_action,
                                       "label": "Duration(in seconds)"})

    def add_all_resources_additive_data(self, scenario_object):
        """Generate a line graph for duration data from each resource created by Rally.
        :param scenario_object: Rally scenario object
        """
        atomic_actions = scenario_object.atomic_actions()
        additive_data_all_actions = []
        for action in atomic_actions:
            additive_data_all_actions.append([action["name"], action["finished_at"] -
                                              action["started_at"]])
        scenario_object.add_output(additive={"title": "Resources atomic action duration line chart",
                                             "description": "Resources trend",
                                             "chart_plugin": "ResourceDurationLines",
                                             "data": additive_data_all_actions,
                                             "label": "Duration(in seconds)",
                                             "axis_label": "Resource count"})

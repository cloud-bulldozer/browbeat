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

from rally.common.plugin import plugin
from rally.task.processing import charts
from rally.task.processing import utils

@plugin.configure(name="ResourceDurationLines")
class ResourceDurationOutputLinesChart(charts.OutputStackedAreaChart):
    """Display resource duration data as generic chart with lines.

    This plugin processes additive data and displays it in HTML report
    as linear chart with X axis bound to iteration number.
    Complete output data is displayed as linear chart as well, without
    any processing.

    Examples of using this plugin in Scenario, for saving output data:

    .. code-block:: python

        self.add_output(
            additive={"title": "Resources atomic action duration line chart",
                      "description": "Resources trend",
                      "chart_plugin": "ResourceDurationLines",
                      "data": [["foo", 12], ["bar", 34]],
                      "label": "Duration(in seconds)",
                      "axis_label": "Resource count"})
    """

    widget = "Lines"

    def add_iteration(self, iteration):
        """Add iteration data.
        This method must be called for each iteration.
        :param iteration: list, resource duration data for current iteration
        """
        atomic_count = {}
        self.max_count = 0
        for name, value in iteration:
            if name not in atomic_count.keys():
                atomic_count[name] = 1
            else:
                atomic_count[name] += 1
            self.max_count = max(self.max_count, atomic_count[name])

        for name, value in iteration:
            if name not in self._data:
                self._data[name] = utils.GraphZipper(self.base_size*self.max_count,
                                                     self.zipped_size)
            self._data[name].add_point(value)

    def zeropad_duration_data(self):
        """Some actions might have been executed more times than other actions
        in the same iteration. Zeroes are appended to make the numbers equal.
        """
        for key in self._data:
            i = len(self._data[key].get_zipped_graph())
            while i < self.base_size*self.max_count:
                i += 1
                self._data[key].add_point(0)

    def render(self):
        """Render HTML from resource duration data"""
        self.zeropad_duration_data()
        render_data = [(name, points.get_zipped_graph())
                       for name, points in self._data.items()]
        return {"title": self.title,
                "description": self.description,
                "widget": self.widget,
                "data": render_data,
                "label": self.label,
                "axis_label": self.axis_label}

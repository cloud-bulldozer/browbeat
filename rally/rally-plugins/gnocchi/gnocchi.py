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

import uuid

from rally.common import logging
from rally_openstack import consts
from rally_openstack import osclients
from rally_openstack import scenario
from rally.task import atomic
from rally.task import context
from rally.task import validation


LOG = logging.getLogger(__name__)


class GnocchiScenario(scenario.OpenStackScenario):

    @atomic.action_timer("gnocchi.archive_policy_list")
    def _archive_policy_list(self, gnocchi_client):
        return gnocchi_client.archive_policy.list()

    @atomic.action_timer("gnocchi.archive_policy_rule_list")
    def _archive_policy_rule_list(self, gnocchi_client):
        return gnocchi_client.archive_policy_rule.list()

    @atomic.action_timer("gnocchi.capabilities_list")
    def _capabilities_list(self, gnocchi_client):
        return gnocchi_client.capabilities.list()

    @atomic.action_timer("gnocchi.archive_policy_create")
    def _create_archive_policy(self, gnocchi_client, name, definition, aggregation_methods):
        archive_policy = {}
        archive_policy['name'] = name
        archive_policy['definition'] = definition
        archive_policy['aggregation_methods'] = aggregation_methods
        return gnocchi_client.archive_policy.create(archive_policy)

    @atomic.action_timer("gnocchi.archive_policy_rule_create")
    def _create_archive_policy_rule(self, gnocchi_client, name, metric_pattern,
                                    archive_policy_name):
        archive_policy_rule = {}
        archive_policy_rule['name'] = name
        archive_policy_rule['metric_pattern'] = metric_pattern
        archive_policy_rule['archive_policy_name'] = archive_policy_name
        return gnocchi_client.archive_policy_rule.create(archive_policy_rule)

    @atomic.action_timer("gnocchi.metric_create")
    def _create_metric(self, gnocchi_client, name=None, archive_policy_name=None, unit=None,
                       resource_id=None):
        metric = {}
        if name:
            metric['name'] = name
        if archive_policy_name:
            metric['archive_policy_name'] = archive_policy_name
        if unit:
            metric['unit'] = unit
        if resource_id:
            metric['resource_id'] = resource_id
        return gnocchi_client.metric.create(metric)

    @atomic.action_timer("gnocchi.resource_create")
    def _create_resource(self, gnocchi_client, resource_type='generic'):
        resource = {}
        resource['id'] = str(uuid.uuid4())
        return gnocchi_client.resource.create(resource_type, resource)

    @atomic.action_timer("gnocchi.resource_type_create")
    def _create_resource_type(self, gnocchi_client, name):
        resource_type = {}
        resource_type['name'] = name
        return gnocchi_client.resource_type.create(resource_type)

    @atomic.action_timer("gnocchi.archive_policy_delete")
    def _delete_archive_policy(self, gnocchi_client, archive_policy_name):
        return gnocchi_client.archive_policy.delete(archive_policy_name)

    @atomic.action_timer("gnocchi.archive_policy_rule_delete")
    def _delete_archive_policy_rule(self, gnocchi_client, archive_policy_rule_name):
        return gnocchi_client.archive_policy_rule.delete(archive_policy_rule_name)

    @atomic.action_timer("gnocchi.metric_delete")
    def _delete_metric(self, gnocchi_client, metric_id):
        return gnocchi_client.metric.delete(metric_id)

    @atomic.action_timer("gnocchi.resource_delete")
    def _delete_resource(self, gnocchi_client, resource_id):
        return gnocchi_client.resource.delete(resource_id)

    @atomic.action_timer("gnocchi._delete_resource_type")
    def _delete_resource_type(self, gnocchi_client, resource_name):
        return gnocchi_client.resource_type.delete(resource_name)

    @atomic.action_timer("gnocchi._metric_aggregation")
    def _metric_aggregation(self, gnocchi_client, metric_ids, aggregation, refresh):
        return gnocchi_client.metric.aggregation(metrics=metric_ids, aggregation=aggregation,
                                                 refresh=refresh)

    @atomic.action_timer("gnocchi.metric_get_measures")
    def _metric_get_measures(self, gnocchi_client, metric_id, aggregation, refresh):
        return gnocchi_client.metric.get_measures(metric=metric_id, aggregation=aggregation,
                                                  refresh=refresh)

    @atomic.action_timer("gnocchi.metric_list")
    def _metric_list(self, gnocchi_client):
        return gnocchi_client.metric.list()

    @atomic.action_timer("gnocchi.resource_list")
    def _resource_list(self, gnocchi_client):
        return gnocchi_client.resource.list()

    @atomic.action_timer("gnocchi.resource_type_list")
    def _resource_type_list(self, gnocchi_client):
        return gnocchi_client.resource_type.list()

    @atomic.action_timer("gnocchi.status_get")
    def _status_get(self, gnocchi_client, detailed=False):
        return gnocchi_client.status.get(detailed)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.archive_policy_list", platform="openstack")
class ArchivePolicyList(GnocchiScenario):

    def run(self):
        """List archive policies from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._archive_policy_list(gnocchi_client)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.archive_policy_rule_list", platform="openstack")
class ArchivePolicyRuleList(GnocchiScenario):

    def run(self):
        """List archive policy rules from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._archive_policy_rule_list(gnocchi_client)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.capabilities_list", platform="openstack")
class CapabilitiesList(GnocchiScenario):

    def run(self):
        """List capabilities from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._capabilities_list(gnocchi_client)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_archive_policy", platform="openstack")
class CreateArchivePolicy(GnocchiScenario):

    def run(self):
        """Create archive policy from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        name = self.generate_random_name()
        definition = [{'granularity': '0:00:01', 'timespan': '1:00:00'}]
        aggregation_methods = ['std', 'count', '95pct', 'min', 'max', 'sum', 'median', 'mean']
        self._create_archive_policy(gnocchi_client, name, definition, aggregation_methods)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_delete_archive_policy", platform="openstack")
class CreateDeleteArchivePolicy(GnocchiScenario):

    def run(self):
        """Create archive policy from Gnocchi client and then delete it."""
        gnocchi_client = self.admin_clients("gnocchi")
        name = self.generate_random_name()
        definition = [{'granularity': '0:00:01', 'timespan': '1:00:00'}]
        aggregation_methods = ['std', 'count', '95pct', 'min', 'max', 'sum', 'median', 'mean']
        self._create_archive_policy(gnocchi_client, name, definition, aggregation_methods)
        self._delete_archive_policy(gnocchi_client, name)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_archive_policy_rule", platform="openstack")
class CreateArchivePolicyRule(GnocchiScenario):

    def run(self):
        """Create archive policy rule from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        name = self.generate_random_name()
        metric_pattern = 'cpu_*'
        archive_policy_name = 'low'
        self._create_archive_policy_rule(gnocchi_client, name, metric_pattern, archive_policy_name)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_delete_archive_policy_rule", platform="openstack")
class CreateDeleteArchivePolicyRule(GnocchiScenario):

    def run(self):
        """Create archive policy rule from Gnocchi client and then delete it."""
        gnocchi_client = self.admin_clients("gnocchi")
        name = self.generate_random_name()
        metric_pattern = 'cpu_*'
        archive_policy_name = 'low'
        self._create_archive_policy_rule(gnocchi_client, name, metric_pattern, archive_policy_name)
        self._delete_archive_policy_rule(gnocchi_client, name)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_metric", platform="openstack")
class CreateMetric(GnocchiScenario):

    def run(self, metric_name=None, archive_policy_name=None, unit=None, resource_id=None):
        """Create metric from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._create_metric(gnocchi_client, metric_name, archive_policy_name, unit, resource_id)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_delete_metric", platform="openstack")
class CreateDeleteMetric(GnocchiScenario):

    def run(self, metric_name=None, archive_policy_name=None, unit=None, resource_id=None):
        """Create metric from Gnocchi client and then delete it."""
        gnocchi_client = self.admin_clients("gnocchi")
        metric = self._create_metric(gnocchi_client, metric_name, archive_policy_name, unit,
                                     resource_id)
        self._delete_metric(gnocchi_client, metric['id'])


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_resource", platform="openstack")
class CreateResource(GnocchiScenario):

    def run(self, resource_type):
        """Create resource from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._create_resource(gnocchi_client, resource_type)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_delete_resource", platform="openstack")
class CreateDeleteResource(GnocchiScenario):

    def run(self, resource_type):
        """Create resource from Gnocchi client and then delete it."""
        gnocchi_client = self.admin_clients("gnocchi")
        resource = self._create_resource(gnocchi_client, resource_type)
        self._delete_resource(gnocchi_client, resource['id'])


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_resource_type", platform="openstack")
class CreateResourceType(GnocchiScenario):

    def run(self):
        """Create resource type from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._create_resource_type(gnocchi_client, self.generate_random_name())


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.create_delete_resource_type", platform="openstack")
class CreateDeleteResourceType(GnocchiScenario):

    def run(self):
        """Create resource type from Gnocchi client and then delete it."""
        gnocchi_client = self.admin_clients("gnocchi")
        resource_type = self._create_resource_type(gnocchi_client, self.generate_random_name())
        self._delete_resource_type(gnocchi_client, resource_type['name'])


@validation.add("required_contexts", contexts=("browbeat_gnocchi_metric_list"))
@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.metric_aggregation", platform="openstack")
class MetricAggregation(GnocchiScenario):

    def run(self, aggregation=None, refresh=False):
        """Get aggregation of metrics from Gnocchi client. The list of metrics to aggregate from
        is determined through a context before the scenario starts.
        """
        gnocchi_client = self.admin_clients("gnocchi")
        metric_index = self.context['iteration'] % len(self.context['metric_ids'])
        self._metric_aggregation(gnocchi_client, [self.context['metric_ids'][metric_index]],
                                 aggregation, refresh)


@validation.add("required_contexts", contexts=("browbeat_gnocchi_metric_list"))
@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.metric_get_measures", platform="openstack")
class MetricGetMeasures(GnocchiScenario):

    def run(self, aggregation=None, refresh=False):
        """Get measures from a metric from Gnocchi client.  The list of metrics to get measures
        from is determined through a context before the scenario starts.
        """
        gnocchi_client = self.admin_clients("gnocchi")
        metric_index = self.context['iteration'] % len(self.context['metric_ids'])
        self._metric_get_measures(gnocchi_client, self.context['metric_ids'][metric_index],
                                  aggregation, refresh)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.metric_list", platform="openstack")
class MetricList(GnocchiScenario):

    def run(self):
        """List metrics from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._metric_list(gnocchi_client)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.resource_list", platform="openstack")
class ResourceList(GnocchiScenario):

    def run(self):
        """List resources from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._resource_list(gnocchi_client)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.resource_type_list", platform="openstack")
class ResourceTypeList(GnocchiScenario):

    def run(self):
        """List resource types from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._resource_type_list(gnocchi_client)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(name="BrowbeatGnocchi.status_get", platform="openstack")
class StatusGet(GnocchiScenario):

    def run(self, detailed):
        """Get status of Gnocchi from Gnocchi client."""
        gnocchi_client = self.admin_clients("gnocchi")
        self._status_get(gnocchi_client, detailed)


@context.configure(name="browbeat_gnocchi_metric_list", order=350)
class BrowbeatGnocchiMetricList(context.Context):
    """Grabs list of metric ids from Gnocchi for use with getting aggregates/measures."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "additionalProperties": False,
        "properties": {
            "all": {
                "type": "boolean",
            }
        }
    }

    def setup(self):
        gnocchi_client = osclients.Clients(self.context["admin"]["credential"]).gnocchi()
        if self.config.get('all'):
            metric_list = gnocchi_client.metric.list()
            self.context['metric_ids'] = [x['id'] for x in metric_list]
            while len(metric_list) >= 1000:
                metric_list = gnocchi_client.metric.list(marker=metric_list[-1]['id'])
                self.context['metric_ids'].extend([x['id'] for x in metric_list])
        else:
            self.context['metric_ids'] = [x['id'] for x in gnocchi_client.metric.list()]
        LOG.debug('Total metric_ids: {}'.format(len(self.context['metric_ids'])))

    def cleanup(self):
        pass

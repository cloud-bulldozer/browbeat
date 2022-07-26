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
from rally_openstack.common import consts
from rally_openstack.task.scenarios.cinder import utils as cinder_utils
from rally_openstack.task.scenarios.nova import utils as nova_utils
from rally_openstack.task.scenarios.vm import utils as vm_utils
from rally.task import scenario
from rally.task import types
from rally.task import validation

LOG = logging.getLogger(__name__)

@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist", platform="openstack")
class NovaBootPersist(nova_utils.NovaScenario):

    def run(self, image, flavor, **kwargs):
        self._boot_server(image, flavor)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_volume",
                    platform="openstack")
class NovaBootPersistWithVolume(nova_utils.NovaScenario, cinder_utils.CinderBasic):

    def run(self, image, flavor, volume_size, **kwargs):
        server = self._boot_server(image, flavor)
        volume = self.cinder.create_volume(volume_size)
        self._attach_volume(server, volume)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay", "browbeat_persist_network"))
@validation.add("required_services",services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_network",
                    platform="openstack")
class NovaBootPersistWithNetwork(nova_utils.NovaScenario):

    def run(self, image, flavor, **kwargs):
        self._boot_server(image, flavor, **kwargs)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay", "browbeat_persist_network"))
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_network_volume",
                    platform="openstack")
class NovaBootPersistWithNetworkVolume(nova_utils.NovaScenario, cinder_utils.CinderBasic):

    def run(self, image, flavor, volume_size, **kwargs):
        server = self._boot_server(image, flavor, **kwargs)
        volume = self.cinder.create_volume(volume_size)
        self._attach_volume(server, volume)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_network_fip",
                    platform="openstack")
class NovaBootPersistWithNetworkFip(vm_utils.VMScenario):

    def run(self, image, flavor, external_net_name, boot_server_kwargs):
        server = self._boot_server(image, flavor, **boot_server_kwargs)
        self._attach_floating_ip(server, external_net_name)


@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_contexts", contexts=("browbeat_delay"))
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={}, name="BrowbeatNova.nova_boot_persist_with_network_volume_fip",
                    platform="openstack")
class NovaBootPersistWithNetworkVolumeFip(vm_utils.VMScenario, cinder_utils.CinderBasic):

    def run(self, image, flavor, volume_size, boot_server_kwargs, external_net_name):
        server = self._boot_server(image, flavor, **boot_server_kwargs)
        volume = self.cinder.create_volume(volume_size)
        self._attach_volume(server, volume)
        self._attach_floating_ip(server, external_net_name)

@types.convert(image={"type": "glance_image"}, flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor", image_param="image")
@validation.add("required_services",services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron", "nova"]},
                    name="BrowbeatNova.nova_boot_in_batches_with_delay",
                    platform="openstack")
class NovaBootInBatchesWithDelay(vm_utils.VMScenario):

    def run(self, image, flavor, delay_time, iterations_per_batch,
            num_iterations_to_delay, num_tenant_networks, concurrency, **kwargs):
        """Boot VMs in batches with delay in between. This scenario is useful for scaling VMs incrementally.
        :param image: image of the VMs to be booted
        :param flavor: flavor of the VMs to be booted
        :param delay_time: int, time in seconds to delay VM boot in between batches
        :param iterations_per_batch: int, number of iterations that can run before delay occurs
        :param num_iterations_to_delay: int, number of iterations to delay
        :param num_tenant_networks: int, number of tenant networks
        :param concurrency: int, concurrency passed to rally runner
        """
        if iterations_per_batch <= num_iterations_to_delay:
            raise Exception("num_iterations_to_delay cannot be greater than iterations_per_batch.")
        if iterations_per_batch <= concurrency:
            raise Exception("concurrency cannot be greater than iterations_per_batch.")
        if (self.context["iteration"] % iterations_per_batch <= num_iterations_to_delay and
           self.context["iteration"] >= iterations_per_batch):
            LOG.info("Iteration {} delaying VM boot for {} seconds".format(
                     self.context["iteration"], delay_time))
            time.sleep(delay_time)
        tenant_network_id = self.context["tenant"]["networks"][((self.context["iteration"]-1)
                                                               % num_tenant_networks)]["id"]
        LOG.info("Iteration {} using tenant network {}".format(self.context["iteration"],
                                                               tenant_network_id))
        kwargs["nics"] = [{"net-id": tenant_network_id}]
        self._boot_server(image, flavor, **kwargs)

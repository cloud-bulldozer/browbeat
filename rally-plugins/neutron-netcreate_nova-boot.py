from rally.task import atomic
from rally.task import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.task import types
from rally.task import utils as task_utils
from rally.task import validation

class NeutronPlugin(neutron_utils.NeutronScenario,
                    nova_utils.NovaScenario, 
                    scenario.Scenario):

    #
    # Create network
    # Attach guest to new network
    # List
    # Cleanup
    #
    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova"]})
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_network_nova_boot(self,image,flavor,network_create_args=None,**kwargs):
        network = self._create_network_and_subnets(network_create_args or {})
        kwargs["nics"] = [{ 'net-id': network[0]['network']['id']}]
        self._boot_server(image, flavor, **kwargs)

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
    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova","neutron"]})
    def create_network_nova_boot(self,image,flavor,num_networks=1,network_create_args=None,
                                 subnet_create_args=None,**kwargs):
        nets=[]
        for net in range(1,num_networks):
            network = self._create_network(network_create_args or {})
            subnet = self._create_subnet(network, subnet_create_args or {})
            nets.append(network)

        kwargs["nics"] = []
        for net in nets:
            kwargs["nics"].append({'net-id':net['network']['id']})

        self._boot_server(image, flavor, **kwargs)

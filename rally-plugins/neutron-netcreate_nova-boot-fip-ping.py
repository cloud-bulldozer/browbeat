from rally.task import atomic
from rally.task import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.plugins.openstack.scenarios.vm import utils as vm_utils 
from rally.task import types
from rally.task import utils as task_utils
from rally.task import validation

class NeutronBootFipPingPlugin(neutron_utils.NeutronScenario,
                    vm_utils.VMScenario,
                    scenario.Scenario):
    #
    # Create network
    # Create subnet
    # Attach to router
    # Attach guest to new network
    # List
    # Ping
    # Cleanup
    #
    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova", "neutron"],
                                 "keypair": {}, "allow_ssh": {}})
    def create_network_nova_boot_ping(self,image,flavor,ext_net,floating=False,router=None,
                                 network_create_args=None,subnet_create_args=None,
                                 **kwargs):
        if router == None:
          router = self._create_router({},ext_net)

        network = self._create_network(network_create_args or {})
        subnet = self._create_subnet(network, subnet_create_args or {})
        self._add_interface_router(subnet['subnet'],router['router'])
        kwargs["nics"] = [{ 'net-id': network['network']['id']}]
        _address = None
        if floating : 
          _guest = self._boot_server_with_fip(image, flavor,True,ext_net, **kwargs)
          _address = _guest[1]['ip'] 
        else:
          self._boot_server(image, flavor,**kwargs)
          _address = ""

        if _address:
          self._wait_for_ping(_address) 
         

        

    @atomic.action_timer("neutronPlugin.create_router")
    def _create_router(self, router_create_args, external_gw=False):
        """Create neutron router.

        :param router_create_args: POST /v2.0/routers request options
        :returns: neutron router dict
        """
        router_create_args["name"] = self.generate_random_name()

        if 'id' in external_gw.keys():
            for network in self._list_networks():
                if network.get("router:external"):
                    if network.get("id") == external_gw["id"]:
                        external_network = network
                        gw_info = {"network_id": external_network["id"],
                                   "enable_snat": True}
                        router_create_args.setdefault("external_gateway_info",
                                                      gw_info)

        else:    
            if external_gw:
                for network in self._list_networks():
                    if network.get("router:external"):
                        external_network = network
                        gw_info = {"network_id": external_network["id"],
                                   "enable_snat": True}
                        router_create_args.setdefault("external_gateway_info",
                                                      gw_info)

        return self.clients("neutron").create_router(
            {"router": router_create_args})


# Rally Plugins Browbeat can use
## Current plugins
### neutron-netcreate_nova-boot
Rally plugin that utilizes both Neutron and Nova scneario
utilities. This Rally plugin will create a network then
launch a guest within that network.

#### Example json
'''
{% set flavor_name = flavor_name or "m1.flavorname" %}
{
    "NeutronPlugin.create_network_nova_boot": [
        {
            "args": {
                "flavor": {
                    "name": "{{flavor_name}}"
                },
                "image": {
                    "name": "image_name"
                },
                "network_create_args": {},
            },
            "runner": {
                "type": "serial",
                "times": 5,
            },
            "context": {
                "users": {
                    "tenants": 1,
                    "users_per_tenant": 1
                },
            },
        }
    ]
}

'''

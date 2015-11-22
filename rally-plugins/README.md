# Rally Plugins Browbeat can use
## Current plugins
### neutron-netcreate_nova-boot
This Rally plugin utilizes both Neutron and Nova utilities This Rally plugin will create a network then. launch a guest within that network. This plugin will also attempt to ping the guest, to make sure connectivity works.

#### Assumptions
For this work, we suggest using the admin tenant. With Rally this can be done by creating a env file with the ExistingUsers field. *** Provide example ***. This plugin also assumes the following networking toplogy :
```
[ Rally Host ] --- Link to tenant nework --- [ Router ] -- [ tenant networks ] -- Guests
```
We suggest this method, so you do not have to have a 1:1 connection:tenant network.

*** The below JSON needs updating to show that we need to pass a router t othe plugin.

#### Example json
```
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
```

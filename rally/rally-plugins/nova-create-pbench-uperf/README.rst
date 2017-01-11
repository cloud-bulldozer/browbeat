Browbeat Rally Plugin: nova-create-pbench-uperf
================================================

Warning:
--------
Please review the "To make this work" section. Skipping any steps will result in failure.

Note:
-----
We do not support more then a single concurrency, and single time.

YML Config:
-----------
This section with describe the args in the nova-create-pbench-uperf.yml

.. code-block:: yaml

      image:
        name: 'pbench-image'
      flavor:
        name: 'm1.small'
      zones:
        server: 'nova:hypervisor-1'
        client: 'nova:hypervisor-2'
      external:
        name: "public"
      user: "root"
      password: "100yard-"
      test_types: "stream"
      protocols: "tcp"
      samples: 1
      test_name: "pbench-uperf-test"

**Starting from the top:**

**`image: name:`** This is the image that you want to Rally to launch in the cloud, this guest should have pbench pre-installed.

**`flavor: name:`** is the size of the guest you want rally to launch. For the sake of being simple

**`zones: server: client:`** This is where you want the guests to be pinned to. This can be the same hypervisor.

**`external: name:`** name of the public network which will be attached to a router that Rally creates.

**`user:`** the user to login to the remote instances

**`password:`** not totally necessary, but the password for the user above.

**`test_types:`** the tests for pbench-uperf to run (stream|rr)

**`protocols:`** which protocols to run through (tcp|udp)

**`test_name:`** give the test a name


Before you begin:
-----------------
1. Create a pbench-image that has PBench preinstalled into the guest.
    1a. Use http://www.x86.trystack.org/dashboard/static/rook/centos-noreqtty.qcow2 image
    1b. You can use : helper-script/pbench-user.file
    2a. This will not setup the image for root access
2. Rally cannot use a snapshot to launch the guest, so export the image you created above, and re-import it.
3. Configure the nova-create-pbench-uperf.yml with the right params.

Rally Standup:
--------------
Rally will build the following:

1. Create Router
2. Create Network/Subnet
3. Set Router gateway to provided Public network
4. Attached newly created network/subnet to newly created Router.

Functions:
----------
1. Launch a PBench Jumphost, assign a floating IP to the Jump Host so Rally can reach it.
2. Launch a pair of guests
3. Run PBench-uperf between the pair of guests
4. Send results

What this sets up:
------------------
.. image:: nova-create-pbench-uperf.png

What do you get out of this?
----------------------------
Here is example output from this work : https://gist.github.com/jtaleric/36b7fbbe93dfcb8f00cced221b366bb0


To make this work:
------------------
- PBench is only _verfied_ to work with root, so the user MUST be root. sudo will also not work.
  root is _ONLY_ needed within the guests that are launched within the cloud

- Must update on the controller(s) `/etc/neutron/policy.json` ::

    create_router:external_gateway_info:enable_snat": "rule:regular_user",

- Must update on the controller(s) `/etc/nova/policy.json` ::

    "os_compute_api:servers:create:forced_host": "",

* Most recently OpenStack Newton Nova switched to having a default `policy.json` so the file will be blank. Simply add this rule above.

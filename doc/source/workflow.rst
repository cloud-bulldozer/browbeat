========
Workflow
========

Workflow is a workload type in Browbeat that allows defining custom OpenStack
test sequences as YAML files. Unlike Rally and Shaker which execute predefined
benchmark scenarios, Workflow lets you define step-by-step operations to create,
manage, and clean up OpenStack resources in a controlled sequence.

Workflow uses the same Rally OpenStack clients (``rally_openstack.osclients``)
under the hood, following the same patterns as Rally's ``NeutronScenario``,
``NovaScenario``, and ``VMScenario`` classes for reliability.

Configuration
-------------

Enable the workflow workload in ``browbeat-config.yaml``:

.. code-block:: yaml

    workloads:
      - name: workflow-scenarios
        enabled: true
        type: workflow
        scenarios:
          - name: basic-network-test
            enabled: true
            file: workflow/examples/basic_network.yaml
          - name: vm-connectivity-test
            enabled: false
            file: workflow/examples/vm_connectivity.yaml

Running Workflow
----------------

::

    (.browbeat-venv)[stack@undercloud browbeat]$ ./browbeat.py workflow

Workflow automatically:

- Loads OpenStack credentials from ``overcloudrc`` (RHOSP) or ``clouds.yaml``
  (RHOSO) - the same source files used to create the Rally deployment
- Adds the rally-venv ``site-packages`` to ``sys.path`` for ``rally_openstack``
  imports
- Sets ``openstack_client_http_timeout`` to 180 seconds (same as Rally)
- Suppresses SSL warnings when ``https_insecure`` is configured

Scenario File Format
--------------------

Scenario files are YAML files with the following structure:

.. code-block:: yaml

    name: "My Test Scenario"
    description: "Description of what this scenario does"

    variables:
      network_name: "test-network"
      cidr: "192.168.100.0/24"

    steps:
      - name: "step-name"
        operation: "neutron.create_network"
        args:
          name: "{{ network_name }}"
          admin_state_up: true
        save_as: "network"
        on_failure: "fail"

**Top-level keys:**

:name: Scenario display name
:description: Optional description
:variables: Key-value pairs accessible via ``{{ variable_name }}`` in step args
:steps: Ordered list of operations to execute

**Step keys:**

:name: Step display name
:operation: Operation to execute (e.g., ``neutron.create_network``)
:args: Arguments passed to the operation handler
:save_as: Save the step result to state under this key (accessible via
    ``{{ key.field }}`` in later steps)
:on_failure: ``fail`` to stop execution, ``continue`` to proceed (default:
    ``continue``)
:wait_for_status: (Nova only) Wait for server to reach this status
:wait_for_delete: (Nova only) Wait for server deletion to complete
:wait_timeout: Timeout in seconds for wait operations (default: 300)

Variable Resolution
-------------------

Variables use Jinja2-style ``{{ }}`` syntax and are resolved from two sources:

1. **Scenario variables** - defined in the ``variables`` section:

   .. code-block:: yaml

       variables:
         network_name: "my-network"

       steps:
         - name: "create-network"
           operation: "neutron.create_network"
           args:
             name: "{{ network_name }}"

2. **Step results** - saved via ``save_as`` and accessed with dot notation:

   .. code-block:: yaml

       steps:
         - name: "create-network"
           operation: "neutron.create_network"
           args:
             name: "my-network"
           save_as: "network"

         - name: "create-subnet"
           operation: "neutron.create_subnet"
           args:
             network_id: "{{ network.id }}"
             cidr: "192.168.100.0/24"

If a name argument is omitted, a random name is auto-generated following Rally's
naming convention (e.g., ``wf_net_a3k9x2m1``).

Supported Operations
--------------------

Neutron (Networking)
~~~~~~~~~~~~~~~~~~~~

All neutron operations follow Rally's ``NeutronScenario``
(``rally_openstack.task.scenarios.neutron.utils``) patterns.

**Network Operations**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``neutron.create_network``
     - ``NeutronScenario._create_network()``
     - None (name auto-generated if omitted)
   * - ``neutron.delete_network``
     - ``NeutronScenario._delete_network()``
     - ``network_id``
   * - ``neutron.list_networks``
     - ``NeutronScenario._list_networks()``
     - None (accepts filter kwargs)

**Subnet Operations**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``neutron.create_subnet``
     - ``NeutronScenario._create_subnet()``
     - ``network_id``, ``cidr``
   * - ``neutron.delete_subnet``
     - ``NeutronScenario._delete_subnet()``
     - ``subnet_id``

**Router Operations**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``neutron.create_router``
     - ``NeutronScenario._create_router()``
     - None (name auto-generated if omitted)
   * - ``neutron.delete_router``
     - ``NeutronScenario._delete_router()``
     - ``router_id``
   * - ``neutron.add_interface_router``
     - ``NeutronScenario._add_interface_router()``
     - ``router_id``, ``subnet_id``
   * - ``neutron.remove_interface_router``
     - ``NeutronScenario._remove_interface_router()``
     - ``router_id``, ``subnet_id``

**Port Operations**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``neutron.create_port``
     - ``NeutronScenario._create_port()``
     - ``network_id``
   * - ``neutron.delete_port``
     - ``NeutronScenario._delete_port()``
     - ``port_id``

**Security Group Operations**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``neutron.create_security_group``
     - ``NeutronScenario._create_security_group()``
     - None (name auto-generated if omitted)
   * - ``neutron.delete_security_group``
     - ``NeutronScenario._delete_security_group()``
     - ``security_group_id``
   * - ``neutron.create_security_group_rule``
     - ``NeutronScenario._create_security_group_rule()``
     - ``security_group_id`` (defaults: direction=ingress, protocol=tcp)

**Floating IP Operations**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``neutron.create_floatingip``
     - ``NeutronScenario._create_floatingip()``
     - ``floating_network_id`` or ``floating_network_name``
   * - ``neutron.delete_floatingip``
     - ``NeutronScenario._delete_floating_ip()``
     - ``floatingip_id``
   * - ``neutron.list_floating_ips``
     - ``NeutronScenario._list_floating_ips()``
     - None (accepts filter kwargs)

Nova (Compute)
~~~~~~~~~~~~~~

All nova operations follow Rally's ``NovaScenario``
(``rally_openstack.task.scenarios.nova.utils``) and ``VMScenario``
(``rally_openstack.task.scenarios.vm.utils``) patterns.

.. note:: The ``image`` and ``flavor`` arguments accept either a **name** (e.g.,
   ``cirros``, ``m1.small``) or a **UUID**. Names are automatically resolved to
   UUIDs via the Glance and Nova APIs, matching Rally's type converter behavior.

**Server Lifecycle**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``nova.boot_server``
     - ``NovaScenario._boot_server()``
     - ``image``, ``flavor`` (name or UUID; waits for ACTIVE by default)
   * - ``nova.boot_server_with_fip``
     - ``VMScenario._boot_server_with_fip()``
     - ``image``, ``flavor`` (name or UUID), ``floating_network``
   * - ``nova.delete_server``
     - ``NovaScenario._delete_server()``
     - ``server_id`` (optional: ``force``, ``wait_for_delete``)
   * - ``nova.create_server``
     - Legacy alias for ``nova.boot_server``
     - Same as ``nova.boot_server``

**Server State**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``nova.stop_server``
     - ``NovaScenario._stop_server()``
     - ``server_id`` (waits for SHUTOFF)
   * - ``nova.start_server``
     - ``NovaScenario._start_server()``
     - ``server_id`` (waits for ACTIVE)

**Server Query**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``nova.show_server``
     - ``NovaScenario._show_server()``
     - ``server_id``
   * - ``nova.list_servers``
     - ``NovaScenario._list_servers()``
     - None (optional: ``detailed``)
   * - ``nova.get_server``
     - Legacy alias for ``nova.show_server``
     - Same as ``nova.show_server``

**Network/Interface**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``nova.attach_floating_ip``
     - ``VMScenario._attach_floating_ip()``
     - ``server_id``, ``floating_network``
   * - ``nova.attach_interface``
     - ``NovaScenario._attach_interface()``
     - ``server_id`` (optional: ``net_id``, ``port_id``)

**Volume**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``nova.attach_volume``
     - ``NovaScenario._attach_volume()``
     - ``server_id``, ``volume_id``
   * - ``nova.detach_volume``
     - ``NovaScenario._detach_volume()``
     - ``server_id``, ``volume_id``

**Infrastructure Query**

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Operation
     - Rally Equivalent
     - Required Args
   * - ``nova.list_hypervisors``
     - ``NovaScenario._list_hypervisors()``
     - None
   * - ``nova.list_flavors``
     - ``NovaScenario._list_flavors()``
     - None

Common (Workflow Control)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Operation
     - Description
   * - ``workflow.wait``
     - Sleep for specified seconds. Args: ``seconds`` (default: 1)
   * - ``workflow.log``
     - Log a message. Args: ``message``, ``level`` (debug/info/warning/error,
       default: info)

Examples
--------

Basic Network Create and Delete
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    name: "Basic Network Test"
    description: "Create a network and subnet, then clean up"

    variables:
      network_name: "test-network"

    steps:
      - name: "create-network"
        operation: "neutron.create_network"
        args:
          name: "{{ network_name }}"
          admin_state_up: true
        save_as: "network"
        on_failure: "fail"

      - name: "create-subnet"
        operation: "neutron.create_subnet"
        args:
          network_id: "{{ network.id }}"
          cidr: "192.168.100.0/24"
          ip_version: 4
        save_as: "subnet"
        on_failure: "fail"

      - name: "wait"
        operation: "workflow.wait"
        args:
          seconds: 5

      - name: "delete-network"
        operation: "neutron.delete_network"
        args:
          network_id: "{{ network.id }}"

Network with Router and Security Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    name: "Network with Router"
    description: "Create network, subnet, router, and security group"

    variables:
      ext_net_id: "your-external-network-id"

    steps:
      - name: "create-network"
        operation: "neutron.create_network"
        args:
          admin_state_up: true
        save_as: "network"
        on_failure: "fail"

      - name: "create-subnet"
        operation: "neutron.create_subnet"
        args:
          network_id: "{{ network.id }}"
          cidr: "10.0.0.0/24"
          ip_version: 4
        save_as: "subnet"
        on_failure: "fail"

      - name: "create-router"
        operation: "neutron.create_router"
        args:
          external_gateway_info:
            network_id: "{{ ext_net_id }}"
            enable_snat: true
        save_as: "router"
        on_failure: "fail"

      - name: "attach-subnet-to-router"
        operation: "neutron.add_interface_router"
        args:
          router_id: "{{ router.id }}"
          subnet_id: "{{ subnet.id }}"
        on_failure: "fail"

      - name: "create-security-group"
        operation: "neutron.create_security_group"
        args:
          name: "test-sg"
        save_as: "sg"
        on_failure: "fail"

      - name: "allow-ssh"
        operation: "neutron.create_security_group_rule"
        args:
          security_group_id: "{{ sg.id }}"
          protocol: "tcp"
          port_range_min: 22
          port_range_max: 22
          remote_ip_prefix: "0.0.0.0/0"

      - name: "allow-icmp"
        operation: "neutron.create_security_group_rule"
        args:
          security_group_id: "{{ sg.id }}"
          protocol: "icmp"
          remote_ip_prefix: "0.0.0.0/0"

Boot VM with Floating IP
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    name: "Boot VM with FIP"
    description: "Create network, boot server, attach floating IP"

    variables:
      image: "cirros"
      flavor: "m1.small"
      ext_network: "public"

    steps:
      - name: "create-network"
        operation: "neutron.create_network"
        args:
          admin_state_up: true
        save_as: "network"
        on_failure: "fail"

      - name: "create-subnet"
        operation: "neutron.create_subnet"
        args:
          network_id: "{{ network.id }}"
          cidr: "192.168.200.0/24"
          ip_version: 4
        save_as: "subnet"
        on_failure: "fail"

      - name: "boot-server"
        operation: "nova.boot_server_with_fip"
        args:
          image: "{{ image }}"
          flavor: "{{ flavor }}"
          floating_network: "{{ ext_network }}"
          nics:
            - net-id: "{{ network.id }}"
        save_as: "vm"
        wait_timeout: 300
        on_failure: "fail"

      - name: "log-result"
        operation: "workflow.log"
        args:
          message: "VM {{ vm.server.name }} booted with FIP {{ vm.fip.ip }}"

      - name: "cleanup-server"
        operation: "nova.delete_server"
        args:
          server_id: "{{ vm.server.id }}"
        wait_for_delete: true
        on_failure: "continue"

      - name: "cleanup-network"
        operation: "neutron.delete_network"
        args:
          network_id: "{{ network.id }}"
        on_failure: "continue"

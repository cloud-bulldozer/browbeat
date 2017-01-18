=============
Plugins
=============

Rally
~~~~~

Context - browbeat_persist_network
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This context creates network resources that persist upon completation of a rally run.  It is used in conjunction with the nova_boot_persist_with_network plugin scenario.  Beware that removal of the network resources created by this context plugin can be a lengthy process so this is best used on "throw-away-test" clouds.

Scenario - nova_boot_persist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This scenario creates instances without a network that persist upon completation of a rally run.  This scenario is best used for excerising the Telemetry systems within an OpenStack Cloud.  Alternatively, it can be used to put idle instances on a cloud for other workloads to compuete for resources.  The scenario is referenced in the telemetry Browbeat configurations in order to build a "stepped" workload that can be used to analyze telemetry performance and scalability.

Scenario - nova_boot_persist_with_network
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This scenario creates instances that are attached to a network and persist upon completation of a rally run. This scenario is best used for excerising the Telemetry systems within an OpenStack Cloud.  It increases the telemetry workload by creating more resources that the telemetry services must collect and process metrics over.  Alternatively, it can be used to put idle instances on a cloud for other workloads to compuete for resources.  The scenario is referenced in the telemetry Browbeat configurations in order to build a "stepped" workload that can be used to analyze telemetry scalability.

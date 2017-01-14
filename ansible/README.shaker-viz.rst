Shaker Data Plane Performance Dashboards
========================================

Two dashboards have been provided with Browbeat for Shaker.

Browbeat Shaker Scenarios with Throughput vs Concurrency
-------------------------------------------------------
This Shaker dashboard aims to present data plane performance of OpenStack VMs
connected in different network topologies in a summarized form. Three distinct
visulizations representing L2, L3 E-W and L3 N-S topologies along with the
corrensponding markdown to exaplain each visualization make the "Browbeat Shaker
Scenarios with Throughput vs Concurrency" dashboard. For each network topology,
average throughput for TCP download and upload in Mbps is expressed vs the VM
conccurency (number of pairs of VMs firing traffic at any given moment). For
example, in the L2 scenario if the average throughput is 4000 Mbps at a
concurrency of 2, it means that each pair of VMs involved average at 4000 Mbps
for the duration of the test, bringing the total throughput to 8000 Mbps(avg
throughput*concurrency).

Browbeat Shaker Cloud Performance Comparison
--------------------------------------------
This Shaker dashboard lets you compare network performance results from various
clouds. This dashboard is ideal if you want to compare data plane performance
with different neutron configurations in different clouds. For each topology, a
visualization comparing ``tcp_download`` and ``tcp_upload`` per cloud name and 
a visualization comparing ping latency per cloud name is generated in the
dashboard along with instructions in markdown for advanced filtering and
querying.



.. note:: You can filter based on ``browbeat_uuid`` and ``shaker_uuid`` to view results 
   from a specific run or shaker scenario only and ``record.concurrency`` and 
   ``record.accommodation`` to filter based on the subest of the test results you
   want to view.



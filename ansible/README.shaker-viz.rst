Shaker Data Plane Performance Dashboard
=======================================

The Shaker dashboard aims to present data plane performance of OpenStack VMs
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

You can filter based on browbeat_uuid and shaker_uuid to view results from a
specific run only.


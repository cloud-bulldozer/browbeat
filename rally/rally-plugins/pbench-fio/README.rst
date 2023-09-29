Block Storage Performance Testing with Pbench FIO
===================================================

Overview
--------

This workload is designed to perform storage-based tests to analyze the read and write throughput achieved by OpenStack VMs backed by Ceph. Cinder provides volumes as additional mounts to the guest machines, and the scenario uses Pbench FIO to perform these tests.

Pbench FIO is utilized to simulate block-based I/O to drives, whether virtual or physical. These drives are presented to the virtual machines using Cinder and Nova.

Customizing FIO Parameters
--------------------------

To customize FIO parameters and better understand their usage, please refer to the [Pbench FIO documentation](https://github.com/distributed-system-analysis/pbench/blob/main/agent/bench-scripts/pbench-fio.md). This documentation provides detailed information on how to configure and pass FIO parameters for your specific testing requirements

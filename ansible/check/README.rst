Browbeat Ansible Checks
=======================

The Browbeat Ansible checks playbook will scan a given deployment to
check for known configuration issues.

Output from Checks
------------------

Once the Checks playbook completes there will be a report generated in
the browbeat results directory.

::

    bug_report.log

This will contain each of the hosts that were scanned, and their known
issues. Some of the issues will have BZ's associated with them, use the
BZ link to learn more about the bug, and how it can impact your
deployment. There will be Checks that do not have a BZ associated, these
are simply suggestions.

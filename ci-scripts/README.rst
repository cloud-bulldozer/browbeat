Table of Contents
=================

-  `CI Structure <#ci-structure>`__
-  `Script Documentation <#script-documentation>`__

   -  `Install and Check <#install-and-check>`__

      -  `Invoking Locally <#invoking-locally>`__

CI Structure
============
For an example Jenkins configuration see `this job <https://ci.centos.org/view/rdo/view/POC/job/poc-browbeat-tripleo-quickstart-mitaka-delorean-full-deploy-minimal/>`_

If you would like to make your own CI job add your CI script to this directory and invoke it as minimally as possible on the Jenkins end, this will help us keep script changes in the repository and better test them before merging.

Script Documentation
====================

Install and Check
-----------------
Currently the main CI script that is run against every commit submittied to the Openstack Gerrit. For each test a fresh Openstack instance is deployed using `TripleO Quickstart <https:github.com/openstack/tripleo-quickstart>`_, Browbeat is then installed. Both of these happen regardless of what was included in the commit. Workload tests are run only if a file diff between the commit and Browbeat master contains the workload name. Success is defined as all processes in the script exiting with exit code 0, note Browbeat will return zero if a test fails its SLA or otherwise fails in a manner that's not total.

To add an additional workload to the script add the workload name to the tools loop near the bottom of the file.

::

    for tool in rally perfkit shaker <tool name>; do


Then add configuration details that run all functions of the added task or plugin to the browbeat-ci.yaml file in ci-scripts/config.

You can view the output of this job `here <https://ci.centos.org/view/rdo/view/POC/job/poc-browbeat-tripleo-quickstart-mitaka-delorean-full-deploy-minimal/>`_

Invoking Locally
~~~~~~~~~~~~~~~~

To run tripleo/install-and-check.sh using your local machine as the driver for a TripleO Quickstart / Browbeat deployment create an empty directory to use as your workspace and point virthost at a machine running CentOS 7+ or RHEL 7+ with at least 32gb of ram.

::

    $ export WORKSPACE=<your empty directory>
    $ export VIRTHOST=<deployment machine hostname>

Navigate to the workspace directory

::

    $ cd $WORKSPACE

Clone the required repositories

::

    $ git clone https://github.com/openstack/browbeat
    $ git clone https://github.com/openstack/tripleo-quickstart/
    $ git clone https://github.com/redhat-openstack/ansible-role-tripleo-inventory

Install the Ansible roles from Github into the virtual environment, as well as a few Python packages

::

    $ virtualenv --no-site-packages $WORKSPACE
    $ source $WORKSPACE/bin/activate
    $ cd $WORKSPACE/ansible-role-tripleo-inventory/
    $ python setup.py install
    $ cd $WORKSPACE/tripleo-quickstart
    $ python setup.py install
    $ pip install --upgrade ansible netaddr

Install the package dependencies, if you're nervous about using root just look inside of quickstart.sh, these are very generic and you might already have all of them installed.

::

    $ sudo bash $WORKSPACE/tripleo-quickstart/quickstart.sh --install-deps

Finally invoke the script and settle in, this command will take about two hours to complete and will place all the relevant ssh credentials and other information to access your instance once the run is complete in the workspace directory.

::

    $ bash $WORKSPACE/browbeat/ci-scripts/tripleo/install-and-check.sh mitaka delorean minimal periodic

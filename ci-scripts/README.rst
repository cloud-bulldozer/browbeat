Table of Contents
=================

-  `CI Structure <#ci-structure>`__
-  `Script Documentation <#script-documentation>`__

   -  `Install and Check <#install-and-check>`__
      -  `Invoking Locally <#invoking-locally>`__
   -  `Browbeat as a Quickstart Extra <#browbeat-as-a-quickstart-extra>`__
      -  `Invoking Locally <#invoking-locally>`__

CI Structure
============
For an example Jenkins configuration see `this job
<https://ci.centos.org/view/rdo/view/POC/job/poc-browbeat-tripleo-quickstart-mitaka-delorean-full-deploy-minimal/>`_

If you would like to make your own CI job add your CI script to this directory
and invoke it as minimally as possible on the Jenkins end, this will help us
keep script changes in the repository and better test them before merging.

Script Documentation
====================

Install and Check
-----------------
Currently the main CI script that is run against every commit submitted to the
Openstack Gerrit. For each test a fresh Openstack instance is deployed using
`TripleO Quickstart <https:github.com/openstack/tripleo-quickstart>`_, Browbeat
is then installed. Both of these happen regardless of what was included in the
commit. Workload tests are run only if a file diff between the commit and
Browbeat master contains the workload name. Success is defined as all processes
in the script exiting with exit code 0, note Browbeat will return zero if a
test fails its SLA or otherwise fails in a manner that's not total.

To add an additional workload to the script add the workload name to the tools
loop near the bottom of the file.

::

    for tool in rally perfkit shaker <tool name>; do


Then add configuration details that run all functions of the added task or
plugin to the ``browbeat-ci.yaml`` file in ``ci-scripts/config``.

You can view the output of this job `here
<https://ci.centos.org/view/rdo/view/POC/job/poc-browbeat-tripleo-quickstart-mitaka-delorean-full-deploy-minimal/>`_

Invoking Locally
~~~~~~~~~~~~~~~~

To run ``tripleo/install-and-check.sh`` using your local machine as the driver
for a TripleO Quickstart / Browbeat deployment create an empty directory to use
as your workspace and point virthost at a machine running CentOS 7+ or RHEL 7+
with at least 32GB of RAM.

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

Install the Ansible roles from Github into the virtual environment, as well as
a few Python packages

::

    $ virtualenv --no-site-packages $WORKSPACE
    $ source $WORKSPACE/bin/activate
    $ cd $WORKSPACE/ansible-role-tripleo-inventory/
    $ python setup.py install
    $ cd $WORKSPACE/tripleo-quickstart
    $ python setup.py install
    $ pip install --upgrade ansible netaddr

Install the package dependencies, if you're nervous about using root just look
inside of ``quickstart.sh``, these are very generic and you might already have
all of them installed.

::

    $ sudo bash $WORKSPACE/tripleo-quickstart/quickstart.sh --install-deps

Finally invoke the script and settle in, as this command will take about two
hours to complete and will place all the relevant ssh credentials and other
information to access your instance once the run is complete in the workspace
directory.

::

    $ bash $WORKSPACE/browbeat/ci-scripts/tripleo/install-and-check.sh mitaka delorean minimal periodic

Browbeat as a Quickstart Extra
------------------------------

`TripleO Quickstart <https:github.com/openstack/tripleo-quickstart>`_ provides
an extensible interface to allow "Extras" to add to to its core functionality
of generating an entirely virtual Openstack Deployment using TripleO. The focus
of this script is to deploy baremetal clouds in continuous integration (CI) for
effective and extensible automated benchmarking.

Invoking Locally
~~~~~~~~~~~~~~~~

Please read `The Extras Documentation
<https://review.openstack.org/#/c/346733/22/doc/source/working-with-extras.rst>`_
for a general background on how TripleO Quickstart Extras operate. Please also
reference `The Baremetal Environments Documentation
<http://images.rdoproject.org/docs/baremetal/>`_ if you need to configure your
job to run on baremetal.

Browbeat provides two playbooks for use with Quickstart
``quickstart-browbeat.yml`` and
``baremetal-virt-undercloud-tripleo-browbeat.yml`` the first playbook is for
deploying an entierly virtual setup on a single baremetal machine. The second
playbook creates a virtual undercloud on a undercloud host machine and deploys a
baremetal overcloud as configured by the users hardware environment.

Dependencies for this script (at least for Fedora 25) are

::

  $ sudo dnf install ansible git python-virtualenv gcc redhat-rpm-config openssl-devel

To run virtual TripleO Quickstart CI set the following environmental vars and
run `quickstart-virt.sh` this will create a TripleO environment and run a short
Browbeat test. Since this is a all virtual setup it is not suggested for
serious benchmarking.

::

  export WORKSPACE={TripleO Quickstart Workspace}
  export RELEASE={release}
  export VIRTHOST={undercloud-fqdn}

  pushd $WORKSPACE/browbeat/ci-scripts/tripleo

  bash quickstart-virt.sh

To run the baremetal CI follow the requisite steps to setup a hardware
environment (this is nontrival) then create a workspace folder and clone
TripleO Quickstart and Browbeat into that workspace. Set the variables below
and then run ``microbrow.sh``.

::

    export WORKSPACE={TripleO Quickstart Workspace}
    export HW_ENV={hw-env}
    export RELEASE={release}
    export GRAPH_HOST={Graphite + grafana host}
    export GRAFANA_USER={username}
    export GRAFANA_PASS={password}
    export CLOUD_NAME={cloud-name}
    export BENCHMARK={benchmark config file ex browbeat-basic.yaml.j2}
    export ELASTIC_HOST={elastic host}
    export VIRTHOST={undercloud-fqdn}

    pushd $WORKSPACE/browbeat/ci-scripts/tripleo

    bash microbrow.sh

Configurable Options
~~~~~~~~~~~~~~~~~~~~

By default a cloud will be setup and a very basic benchmark will be run and all
results will be placed only in the ``browbeat/results`` folder on the virtual
undercloud.

If configured to use Elasticsearch metadata and benchmarks results will be
inserted into Elasticsearch for easier visualization and storage. If Graphana is
enabled performance metrics will be gathered from all cloud nodes and stored
into the configured graphite instance to be processed by the Grafana dashboards
created using the given username and password.

These dashboards will be automatically overwritten each run to reflect the
number of nodes in your cloud and other changes that may occur between runs.

=====================
Browbeat as a CI tool
=====================

If you would like to make your own CI job add your bootstrapping script to
`ci-scripts/<openstack installer>` and Ansible/Python components into normal
locations in the repository. Try and provide as many defaults as possible so
that job definitions on the Jenkins end can remain small and easily defined.
this will help us keep script changes in the repository and better test them
before merging.

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
and then run ``microbrow.sh``. There must be an all.yml file in the HW_ENV
directory for overriding some browbeat variables with ones specific to the CI
environment.

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

If enabled these dashboards will be automatically overwritten each run to reflect
the number of nodes in your cloud and other changes that may occur between runs.

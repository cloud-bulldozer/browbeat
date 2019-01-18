============
Contributing
============

Contributions are most welcome!  You must first create a
Launchpad account and `follow the instructions here <https://docs.openstack.org/infra/manual/developers.html#account-setup>`_
to get started as a new OpenStack contributor.

Once you've signed the contributor license agreement and read through
the above documentation, add your public SSH key under the 'SSH Public Keys'
section of review.openstack.org_.

.. _review.openstack.org: https://review.openstack.org/#/settings/

You can view your public key using:

::

    $ cat ~/.ssh/id_*.pub

Setup
`````

Set your username and email for review.openstack.org:

::

    $ git config --global user.email "example@example.com"
    $ git config --global user.name "example"
    $ git config --global --add gitreview.username "example"


Next, Clone the github repository:

::

    $ git clone https://github.com/openstack/browbeat.git

You need to have git-review in order to be able to submit patches using
the gerrit code review system. You can install it using:

::

    $ sudo yum install git-review

To set up your cloned repository to work with OpenStack Gerrit

::

    $ git review -s


Making changes
``````````````

It's useful to create a branch to do your work, name it something
related to the change you'd like to introduce.

::

    $ cd browbeat
    $ git branch my_special_enhancement
    $ git checkout !$

Now you can make your changes and then commit.

::

    $ git add /path/to/files/changed
    $ git commit

Use a descriptive commit title followed by an empty space.
You should type a small justification of what you are
changing and why.

Local testing
`````````````

Before submitting code to Gerrit you *should* do at least some minimal local
testing, like running ``tox -e linters``. This could be automated if you
activate `pre-commit <https://pre-commit.com/>`__ hooks::

    pip install --user pre-commit
    # to enable automatic run on commit:
    pre-commit install --install-hooks
    # to uninstall hooks
    pre-commit uninstall

Please note that the pre-commit feature is available only on repositories that
do have `.pre-commit-config.yaml <https://github.com/openstack/browbeat/blob/master/.pre-commit-config.yaml>`__ file.

Running ``tox -e linters`` is recommended as it may include additional linting
commands than just pre-commit. So, if you run tox you don't need to run
pre-commit manually.

Implementation of pre-commit is very fast and saves a lot of disk space
because internally it does cache any linter-version and reuses it between
repositories, as opposed to tox which uses environments unique to each
repository (usually more than one). Also by design pre-commit always pins
linters, making less like to break code because linter released new version.

Another reason why pre-commit is very fast is because it runs only
on modified files. You can force it to run on the entire repository via
`pre-commit run -a` command.

Upgrading linters is done via ``pre-commit autoupdate`` but this should be
done only as a separate change request.


Submit Changes
``````````````

Now you're ready to submit your changes for review:

::

    $ git review


If you want to make another patchset from the same commit you can
use the amend feature after further modification and saving.

::

    $ git add /path/to/files/changed
    $ git commit --amend
    $ git review

Changes to a review
```````````````````

If you want to submit a new patchset from a different location
(perhaps on a different machine or computer for example) you can
clone the Browbeat repo again (if it doesn't already exist) and then
use git review against your unique Change-ID:

::

    $ git review -d Change-Id

Change-Id is the change id number as seen in Gerrit and will be
generated after your first successful submission.

The above command downloads your patch onto a separate branch. You might
need to rebase your local branch with remote master before running it to
avoid merge conflicts when you resubmit the edited patch.  To avoid this
go back to a "safe" commit using:

::

    $ git reset --hard commit-number

Then,

::

    $ git fetch origin

::

    $ git rebase origin/master

Make the changes on the branch that was setup by using the git review -d
(the name of the branch is along the lines of
review/username/branch_name/patchsetnumber).

Add the files to git and commit your changes using,

::

    $ git commit --amend

You can edit your commit message as well in the prompt shown upon
executing above command.

Finally, push the patch for review using,

::

    $ git review

Adding functionality
--------------------

If you are adding new functionality to Browbeat please add testing for that functionality in.

::

    $ ci-scripts/install-and-check.sh

See the README.rst in the ci-scripts folder for more details on the structure of the script and how to add additional tests.

Contributing to stockpile
-------------------------

We currently use `featureset001 <https://github.com/redhat-performance/stockpile/blob/master/config/featureset001.yml>`_ of
`stockpile <https://github.com/redhat-performance/stockpile>`_
to gather config. Please follow `instructions <https://github.com/redhat-performance/stockpile#contributing>`_
to contribute to stockpile.

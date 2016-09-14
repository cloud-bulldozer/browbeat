ElasticSearch Configuration for Browbeat
-----------------------------------------

**+ templates/**

Will contain Elasticsearch templates to account for things like the Browbeat UUID.
These Templates will be installed if you run through our Elasticsearch installer. If
you already have a Elasticsearch Host, you can install them by running the following::

    $ cd ../ansible
    $ vi install/group_vars/all.yml
    # Update your es_ip
    $ ansible-playbook -i hosts install/es-template.yml


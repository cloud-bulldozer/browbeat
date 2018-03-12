ElasticSearch / Kibana Template
----------------------------------

to use v5 templates, set 'elastic5: true' in ansible/install/group_vars/all

Template to instruct elasticsearch & Kibana to not processes some of our fields. For example, our UUIDs would turn into multiple strings due the default tokenizer's use of '-', '.', '/', etc. as token separators.

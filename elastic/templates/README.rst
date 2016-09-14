ElasticSearch / Kibana Template
----------------------------------

Template to instruct elasticSearch & Kibana to not processes some of our fields. For example, our UUIDs would turn into multiple strings due the default tokenizer's use of '-', '.', '/', etc. as token separators.

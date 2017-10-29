# OpenStack Browbeat Kibana visualization
-----------------------------------------
To import these Visualizations, you need Kibana 4.1 or greater.

## How to install?
-------------------
Use the provided ansible playbook in ansible/install in order to install the Kibana Viz.

## Assumptions
--------------
This work assumes you are using :

- Browbeat to run Rally workloads
- Browbeat Gather scripts for Metadata

Without the two pieces of information above, your milage may vary.

Also, this work assumes you are using the default browbeat-rally-YYYY.MM.DD ElasticSearch index. If that is not the case, update the jsons.

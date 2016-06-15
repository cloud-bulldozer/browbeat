Setting up a CFME or ManageIQ VM for All-In-One Performance Monitoring
======================================================================

1. Deploy ManageIQ/CFME appliance
2. Add additional disk to host Graphite's whisper database, mount disk
   at /var/lib/carbon
3. Clone browbeat

::

   [root@manageiq ~]# git clone https://github.com/jtaleric/browbeat.git``
   [root@manageiq ~]# cd browbeat/ansible``

4. Create ansible inventory file

::

   [graphite]
   localhost ansible_connection=local

   [grafana]
   localhost ansible_connection=local

   [cfme-all-in-one]
   localhost ansible_connection=local

5. Install ansible

::

   [root@manageiq ansible]# easy_install pip
   [root@manageiq ansible]# yum install -y python-devel gcc-c++
   [root@manageiq ansible]# pip install ansible

6. Setup installation variables at *install/group_vars/all.yml* by modifying
following variables

::

   graphite_host: localhost
   graphite_port: 9000
   graphite_prefix: manageiq
   grafana_host: localhost
   grafana_port: 9001

7. Run playbooks for collectd/graphite/grafana install

::

   [root@manageiq ansible]# ansible-playbook -i hosts install/graphite.yml
   [root@manageiq ansible]# ansible-playbook -i hosts install/grafana.yml
   [root@manageiq ansible]# ansible-playbook -i hosts install/collectd-generic.yml --tags="cfme-all-in-one"

8. Upload dashboards via ansible

::

   [root@manageiq ansible]# ansible-playbook -i hosts install/dashboards-generic.yml

9. Enjoy your now performance monitored CFME/ManageIQ appliance, view
   grafana dashboards at http://(manageiq-ip-address):9001/

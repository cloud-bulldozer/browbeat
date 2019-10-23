FROM centos:7

RUN yum update -y && \
    yum clean all && \
    yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm && \
    yum install -y centos-release-opstools && \
    yum install -y collectd collectd-turbostat collectd-disk collectd-apache collectd-ceph \
     collectd-mysql collectd-python collectd-ping && \
    yum install -y sysstat && \
    yum install -y python2-pip python2-devel && \
    pip install pyrabbit && \
    yum install -y libdbi-dbd-mysql collectd-dbi


ADD files/collectd_ceph_storage.py /usr/local/bin/collectd_ceph_storage.py
ADD files/collectd_gnocchi_status.py /usr/local/bin/collectd_gnocchi_status.py
ADD files/collectd_rabbitmq_monitoring.py /usr/local/bin/collectd_rabbitmq_monitoring.py
ADD files/collectd_swift_stat.py /usr/local/bin/collectd_swift_stat.py

ADD config/collectd.conf /etc/collectd.conf

CMD ["collectd", "-f"]

FROM registry.centos.org/centos:7

RUN yum update -y && \
    yum clean all && \
    yum groupinstall -y development tools && \
    yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm && \
    yum install -y centos-release-opstools && \
    yum install -y collectd collectd-turbostat collectd-disk collectd-apache collectd-ceph \
     collectd-mysql collectd-python collectd-ping && \
    yum install -y sysstat && \
    yum install -y python2-pip python2-devel && \
    pip install --upgrade 'pip<20' && \
    pip install pyrabbit && \
    yum install -y libdbi-dbd-mysql collectd-dbi && \
    yum install -y https://cbs.centos.org/kojifiles/packages/openvswitch/2.11.0/4.el7/x86_64/openvswitch-2.11.0-4.el7.x86_64.rpm && \
    yum install -y libibverbs && \
    yum install -y sudo

RUN useradd stack
RUN echo stack | passwd stack --stdin
RUN echo "stack ALL=(root) NOPASSWD:ALL" | tee -a /etc/sudoers.d/stack
RUN chmod 0440 /etc/sudoers.d/stack


ADD files/collectd_ceph_storage.py /usr/local/bin/collectd_ceph_storage.py
ADD files/collectd_gnocchi_status.py /usr/local/bin/collectd_gnocchi_status.py
ADD files/collectd_rabbitmq_monitoring.py /usr/local/bin/collectd_rabbitmq_monitoring.py
ADD files/collectd_swift_stat.py /usr/local/bin/collectd_swift_stat.py
ADD files/collectd_pacemaker_monitoring.py /usr/local/bin/collectd_pacemaker_monitoring.py
ADD files/ovs_flows.sh /usr/local/bin/ovs_flows.sh
ADD files/ovn_monitoring.sh /usr/local/bin/ovn_monitoring.sh

ADD config/collectd.conf /etc/collectd.conf

CMD ["collectd", "-f"]

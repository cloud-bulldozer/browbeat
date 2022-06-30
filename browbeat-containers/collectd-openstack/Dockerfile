FROM quay.io/centos/centos:stream8

RUN dnf clean all && \
    dnf group install -y "Development Tools" --nobest && \
    dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && \
    dnf install -y centos-release-opstools && \
    dnf install -y collectd collectd-turbostat collectd-disk collectd-apache collectd-ceph \
     collectd-mysql collectd-python collectd-ping python3-sqlalchemy-collectd && \
    dnf install -y sysstat && \
    dnf install -y python3-pip python3-devel && \
    pip3 install --upgrade pip && \
    pip3 install pyrabbit && \
    dnf install -y libdbi-dbd-mysql collectd-dbi && \
    dnf install -y centos-release-openstack-ussuri && \
    dnf config-manager --set-enabled powertools && \
    dnf install -y openvswitch libibverbs && \
    dnf install -y passwd && \
    dnf install -y ceph-common && \
    dnf install -y sudo

RUN useradd stack
RUN echo stack | passwd stack --stdin
RUN echo "stack ALL=(root) NOPASSWD:ALL" | tee -a /etc/sudoers.d/stack
RUN chmod 0440 /etc/sudoers.d/stack


ADD files/collectd_ceph_storage.py /usr/local/bin/collectd_ceph_storage.py
ADD files/collectd_gnocchi_status.py /usr/local/bin/collectd_gnocchi_status.py
ADD files/collectd_rabbitmq_monitoring.py /usr/local/bin/collectd_rabbitmq_monitoring.py
ADD files/collectd_swift_stat.py /usr/local/bin/collectd_swift_stat.py
ADD files/collectd_pacemaker_monitoring.py /usr/local/bin/collectd_pacemaker_monitoring.py
ADD files/collectd_iostat_python.py /usr/local/bin/collectd_iostat_python.py
ADD files/collectd_ovn_raft_monitoring.py /usr/local/bin/collectd_ovn_raft_monitoring.py
ADD files/ovs_flows.sh /usr/local/bin/ovs_flows.sh
ADD files/ovn_monitoring.sh /usr/local/bin/ovn_monitoring.sh

ADD config/collectd.conf /etc/collectd.conf

CMD ["collectd", "-f"]

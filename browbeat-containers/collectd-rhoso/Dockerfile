FROM quay.io/centos/centos:stream9

RUN dnf clean all && \
    dnf group install -y "Development Tools" --nobest && \
    dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm && \
    dnf install -y centos-release-opstools && \
    dnf install -y collectd collectd-turbostat collectd-disk collectd-apache collectd-ceph \
     collectd-mysql collectd-python collectd-ping collectd-virt python3-sqlalchemy-collectd --nobest && \
    dnf install -y sysstat && \
    dnf install -y python3-pip python3-devel && \
    pip3 install --upgrade pip && \
    pip3 install pyrabbit && \
    dnf install -y perl-DBD-MySQL collectd-dbi && \
    dnf install -y centos-release-openstack-bobcat && \
    dnf config-manager --set-enabled crb && \
    dnf install -y openvswitch libibverbs && \
    dnf install -y passwd && \
    dnf install -y ceph-common && \
    dnf install -y sudo && \
    curl -o /tmp/oc-client.tar.gz https://mirror.openshift.com/pub/openshift-v4/clients/ocp/4.12.60/openshift-client-linux-4.12.60.tar.gz && \
    cd /tmp && tar -xf oc-client.tar.gz && mv oc /usr/local/bin/ && rm kubectl oc-client.tar.gz

RUN useradd stack
RUN echo stack | passwd stack --stdin
RUN echo "stack ALL=(root) NOPASSWD:ALL" | tee -a /etc/sudoers.d/stack
RUN chmod 0440 /etc/sudoers.d/stack
RUN rm /etc/collectd.d/virt.conf

ADD files/ovn_monitoring.sh /usr/local/bin/ovn_monitoring.sh
ADD files/collectd_iostat_python.py /usr/local/bin/collectd_iostat_python.py
ADD files/collectd_ovn_raft_monitoring.py /usr/local/bin/collectd_ovn_raft_monitoring.py

CMD ["collectd", "-f"]

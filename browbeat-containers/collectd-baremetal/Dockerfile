FROM quay.io/centos/centos:stream8

RUN dnf update -y && \
    dnf clean all && \
    dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && \
    dnf install -y centos-release-opstools && \
    dnf install -y collectd collectd-turbostat collectd-disk

ADD config/collectd.conf /etc/collectd.conf

CMD ["collectd", "-f"]

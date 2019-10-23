FROM centos:7

FROM centos:7

RUN yum update -y && \
    yum clean all && \
    yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm && \
    yum install -y centos-release-opstools && \
    yum install -y collectd

ADD config/collectd.conf /etc/collectd.conf

CMD ["collectd", "-f"]

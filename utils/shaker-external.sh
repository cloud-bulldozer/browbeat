#!/bin/bash
# Run as root to setup a shaker-server to run external network tests with
yum install -y epel-release
yum install -y wget iperf iperf3 gcc gcc-c++ python-devel screen zeromq zeromq-devel
wget https://github.com/HewlettPackard/netperf/archive/netperf-2.7.0.tar.gz
tar xvzf netperf-2.7.0.tar.gz
pushd netperf-netperf-2.7.0
./configure --enable-demo=yes
make
make install
popd
easy_install pip
pip install pbr flent pyshaker-agent
cat<<'EOF' >> /etc/systemd/system/iperf.service
[Unit]
Description=iperf Service
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/iperf -s
[Install]
WantedBy=multi-user.target
EOF
cat<<'EOF' >> /etc/systemd/system/iperf3.service
[Unit]
Description=iperf3 Service
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/iperf3 -s
[Install]
WantedBy=multi-user.target
EOF
cat<<'EOF' >> /etc/systemd/system/netperf.service
[Unit]
Description="Netperf netserver daemon"
After=network.target
[Service]
ExecStart=/usr/local/bin/netserver -D
[Install]
WantedBy=multi-user.target
EOF
systemctl start iperf
systemctl enable iperf
systemctl start iperf3
systemctl enable iperf3
systemctl start netperf
systemctl enable netperf


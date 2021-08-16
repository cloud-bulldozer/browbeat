#!/usr/bin/python3
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import sys
import time

from scapy.all import srp
from scapy.all import Ether
from scapy.all import ARP
from scapy.all import sendp
from scapy.all import Dot1Q
from scapy.all import IP
from scapy.all import ICMP


LOG = logging.getLogger(__name__)


def _send_icmp(dst_ip, dst_mac, src_ip, src_mac, iface, vlan):
    # send 1 icmp packet so that dest VM can send ARP packet to resolve gateway
    sendp(Ether(dst=dst_mac, src=src_mac)/Dot1Q(vlan=int(vlan))/IP(dst=dst_ip)/ICMP(),
          iface=iface, verbose=0)
    bcast = "ff:ff:ff:ff:ff:ff"
    # Send GARP using ARP reply method
    sendp(Ether(dst=bcast,src=src_mac)/Dot1Q(vlan=int(vlan))/ARP(
        op=2,psrc=src_ip, hwsrc=src_mac, hwdst=src_mac, pdst=src_ip), iface=iface, verbose=0)
    # send ICMP and validate reply
    ans, unans = srp(Ether(dst=dst_mac, src=src_mac)/Dot1Q(vlan=int(vlan))/IP(dst=dst_ip)/ICMP(),
                     iface=iface, timeout=5, verbose=0)
    if (str(ans).find('ICMP:0') == -1):
        for snd, rcv in ans:
            if (rcv.summary().find(dst_ip) != -1):
                LOG.info("Ping to {} is succesful".format(dst_ip))
                return True
    return False


def main(args):
    dst_ip, dst_mac, src_ip, src_mac, iface, vlan = args[1:]
    attempts = 0
    max_attempts = 120
    while attempts < max_attempts:
        if _send_icmp(dst_ip, dst_mac, src_ip, src_mac, iface, vlan):
            LOG.info("Ping to {} is succesful".format(dst_ip))
            return 0
        LOG.info("Ping to {} is failed, attempt {}".format(dst_ip, attempts))
        attempts += 1
        time.sleep(5)
    return 1


if __name__ == "__main__":
    main(sys.argv)

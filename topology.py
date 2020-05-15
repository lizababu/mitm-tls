#!/usr/bin/python3

from mininet.net import Mininet, Containernet
from mininet.node import Host, OVSBridge, Node, Controller, Docker, UserSwitch, OVSSwitch
from mininet.nodelib import NAT
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import Intf
from subprocess import call
import subprocess

def myNetwork():
    net = Containernet(controller=Controller)

    info( '*** Adding controller\n' )
    net.addController(name='c0')

    info( '*** Add switches\n')
    s1 = net.addSwitch('s1', cls=OVSSwitch)

    info( '*** Add hosts\n')
    # attacker 2 docker containers
    mn_args = {
        "network_mode": "none",
        "dimage": "mitm/https",
        "dcmd": "./start_app.sh",
        "ip": "192.168.16.2/24",
    }
    H1 = net.addDocker('attacker', **mn_args)
    mn_args = {
        "network_mode": "none",
        "dimage": "mitm/https",
        "dcmd": "./start_app.sh",
        "ip": "192.168.16.3/24",
    }
    H2 = net.addDocker('victim', **mn_args)

    info( '*** Add links\n')
    net.addLink( H1, s1 )
    net.addLink( H2, s1 )

    info ('*** Add Internet access\n')
    mn_args = {
        "ip": "192.168.16.1/24",
    }
    nat = net.addHost( 'nat0', cls=NAT, inNamespace=False, subnet='192.168.16.0/24', **mn_args )
    # Connect the nat to the switch
    net.addLink( nat, s1 )

    info( '*** Starting network\n')
    net.start()
    H1.cmd('ip r a default via 192.168.16.1')
    H2.cmd('ip r a default via 192.168.16.1')

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    myNetwork()

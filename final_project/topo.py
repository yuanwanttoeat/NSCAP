#!/usr/bin/python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel

class MyTopo(Topo):
    def build(self):
        # Add hosts and switches
        h1 = self.addHost('h1')
        h2 = self.addHost('h2', mac='00:00:00:00:00:22')
        h3 = self.addHost('h3', mac='00:00:00:00:00:23')
        h4 = self.addHost('h4', mac='00:00:00:00:00:24')
        s1 = self.addSwitch('s1')

        # Add links
        self.addLink(s1, h1)
        self.addLink(s1, h1)
        self.addLink(s1, h2)
        self.addLink(s1, h3)
        self.addLink(s1, h4)

def run():
    # Create network
    topo = MyTopo()
    net = Mininet(topo=topo, controller=RemoteController, link=TCLink)

    # Add controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    # Build and start network
    net.build()
    c0.start()
    net.get('s1').start([c0])

    # Open terminals
    net.startTerms()

    # Run CLI
    CLI(net)

    # Stop network
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()

topos = { 'mytopo': ( lambda: MyTopo() ) }

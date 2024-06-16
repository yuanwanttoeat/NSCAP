from mininet.topo import Topo

class MyTopo( Topo ):

    def build( self ):
        "Create custom topo."

        # Add hosts and switches
        h1 = self.addHost( 'h1', ip = "10.0.0.1" )
        h2 = self.addHost( 'h2', ip = "10.0.0.2" )
        h3 = self.addHost( 'h3', ip = "10.0.0.3" )
        h4 = self.addHost( 'h4', ip = "10.0.0.4" )
        s1 = self.addSwitch( 's1' )

        # Add links
        self.addLink(h1, s1, port1=1, port2=1)
        self.addLink(h2, s1, port1=1, port2=2)
        self.addLink(h3, s1, port1=1, port2=3)
        self.addLink(h4, s1, port1=1, port2=4)

topos = { 'mytopo': ( lambda: MyTopo() ) }
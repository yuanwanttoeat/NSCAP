from mininet.topo import Topo

class MyTopo( Topo ):

    def build( self ):
        "Create custom topo."

        # Add hosts and switches
        h5 = self.addHost( 'h5', ip = "10.0.0.5" )
        h6 = self.addHost( 'h6', ip = "10.0.0.6" )
        h7 = self.addHost( 'h7', ip = "10.0.0.7" )
        h8 = self.addHost( 'h8', ip = "10.0.0.8" )
        s2 = self.addSwitch( 's2' )

        # Add links
        self.addLink(h5, s2, port1=1, port2=1)
        self.addLink(h6, s2, port1=1, port2=2)
        self.addLink(h7, s2, port1=1, port2=3)
        self.addLink(h8, s2, port1=1, port2=4)

topos = { 'mytopo': ( lambda: MyTopo() ) }
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import in_proto

DEFAULT_TABLE = 0
FILTER_TABLE_1 = 1
FILTER_TABLE_2 = 2
FORWARD_TABLE = 3

class ExampleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ExampleSwitch13, self).__init__(*args, **kwargs)
        # initialize mac address table.
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # default table go to filter table 1
        match = parser.OFPMatch()
        inst = [parser.OFPInstructionGotoTable(FILTER_TABLE_1)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=DEFAULT_TABLE,
                                priority=0, match=match, instructions=inst)
        datapath.send_msg(mod)

        # filter icmp packet to filter table 2
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_proto=in_proto.IPPROTO_ICMP)
        inst = [parser.OFPInstructionGotoTable(FILTER_TABLE_2)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_1,
                                priority=1, match=match, instructions=inst)
        datapath.send_msg(mod)
        
        # Not icmp packet go to forward table
        match = parser.OFPMatch()
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_1,
                                priority=0, match=match, instructions=inst)
        datapath.send_msg(mod)
        
        # ''' ~~~ block in_port 3 and 4 ~~~
        # filter packet from target port: port 3 and port 4
        match = parser.OFPMatch(in_port=3)
        inst = []
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2,
                                priority=10, match=match, instructions=inst)
        datapath.send_msg(mod)
        
        match = parser.OFPMatch(in_port=4)
        inst = []
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2,
                                priority=10, match=match, instructions=inst)
        datapath.send_msg(mod)
        
        # filter table 2 go to forward table
        match = parser.OFPMatch()
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2,
                                priority=0, match=match, instructions=inst)
        datapath.send_msg(mod)
        # ~~~ block in_port 3 and 4 ~~~ ''' 
        


        ''' ~~~ allow only port 1 and 2 ~~~
        match = parser.OFPMatch(in_port=1)
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2,
                                priority=10, match=match, instructions=inst)
        datapath.send_msg(mod)
        
        match = parser.OFPMatch(in_port=2)
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2,
                                priority=10, match=match, instructions=inst)
        datapath.send_msg(mod)
        
        match = parser.OFPMatch()
        inst = []
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FILTER_TABLE_2,
                                priority=0, match=match, instructions=inst)
        datapath.send_msg(mod)
        ~~~ allow only port 1 and 2 ~~~ ''' 

        # forward table install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=FORWARD_TABLE, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # get Datapath ID to identify OpenFlow switches.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # analyse the received packets using the packet library.
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src

        # get the received port number from packet_in message.
        in_port = msg.match['in_port']

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        # if the destination mac address is already learned,
        # decide which port to output the packet, otherwise FLOOD.
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # construct action list.
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time.
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        # construct packet_out message and send it.
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=in_port, actions=actions,
                                  data=msg.data)
        datapath.send_msg(out)
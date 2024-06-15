import sys
import time
import socket
import struct
import pickle
import threading
from dataclasses import dataclass

# OSPF packet types
HELLO_PACKET = 1
DBD_PACKET = 2
LSR_PACKET = 3
LSU_PACKET = 4
TEXT_PACKET = 5

# OSPF neighbor states
DOWN_STATE = "Down"
INIT_STATE = "Init"
EXCHANGE_STATE = "Exchange"
FULL_STATE = "Full"

# Routing table entry types
STATIC_ROUTE = 1
OSPF_ROUTE = 2

def pickle_bytes(data):
    return pickle.dumps(data)

def unpickle_bytes(data):
    return pickle.loads(data)

def logger(message):
    print(f"{time.strftime('%H:%M:%S')} - {message}")

def debug(message):
    print(f"\033[1;32m[LOG] {time.strftime('%H:%M:%S')} - {message}\033[0m")

@dataclass
class LinkStateAdvertisement:
    link_id: int
    seq: int
    # metric: int
    metrics: dict[int, int]
    received_time: int

    def __str__(self):
        return f"LSA {self.link_id} {self.seq} {self.metrics}"

@dataclass
class DBD:
    router_id: int
    sequence_number: int
    link_state_advertisements: list[LinkStateAdvertisement]

@dataclass
class LSUPacket:
    link_state_advertisements: list[LinkStateAdvertisement]

@dataclass
class HelloPacket:
    router_id: int
    already_seen: bool
    ack: bool

@dataclass
class LSRPacket:
    request_router_ids: list[int]

@dataclass
class OSPFPacketInfo:
    source_router_id: int
    destination_router_id: int

@dataclass
class OSPFPacket:
    source_router_id: int
    destination_router_id: int
    packet_type: int
    packet_length: int
    packet_data: bytes

class LSDB:
    def __init__(self, router_id):
        self.lsas = {}
        self.lsas[router_id] = LinkStateAdvertisement(router_id, 0, {}, time.time())

    def add_lsa(self, lsa):
        if lsa.link_id in self.lsas:
            existing_lsa = self.lsas[lsa.link_id]
            if lsa.seq > existing_lsa.seq:
                logger(f"update LSA {lsa.link_id} {lsa.seq}")
                self.lsas[lsa.link_id] = lsa
        else:
            logger(f"add LSA {lsa.link_id} {lsa.seq}")
            self.lsas[lsa.link_id] = lsa

    def update_lsa(self, router_id, metrics):
        if router_id in self.lsas:
            lsa = self.lsas[router_id]
            lsa.metrics = {**lsa.metrics, **metrics}
            lsa.seq += 1
            lsa.received_time = time.time()
            logger(f"update LSA {router_id} {lsa.seq}")
        else:
            logger(f"add LSA {router_id} 1")
            self.lsas[router_id] = LinkStateAdvertisement(router_id, 1, metrics, time.time())

    def update_lsa_on_basis(self, router_id, metrics):
        if router_id in self.lsas:
            lsa = self.lsas[router_id]
            lsa.metrics = {**lsa.metrics, **metrics}
            lsa.seq += 1
            lsa.received_time = time.time()
            # logger(f"update LSA {router_id} {lsa.seq}")
        else:
            # logger(f"add LSA {router_id} 1")
            self.lsas[router_id] = LinkStateAdvertisement(router_id, 1, metrics, time.time())

    def remove_lsa(self, link_id):
        if link_id in [lsa.link_id for lsa in self.lsas.values()]:
            logger(f"remove LSA {link_id}")
            del self.lsas[link_id]

    def get_lsa(self, link_id):
        for lsa in self.lsas.values():
            if lsa.link_id == link_id:
                return lsa
        return None

@dataclass
class RoutingTableEntry:
    destination_router_id: int
    next_hop_router_id: int
    cost: int
    type: int

    def __eq__(self, other):
        return self.destination_router_id == other.destination_router_id and self.cost == other.cost and self.next_hop_router_id == other.next_hop_router_id and self.type == other.type

class RoutingTable:
    def __init__(self):
        self.table: list[RoutingTableEntry] = []

    def update(self, type, new_table):
        old_table = [entry for entry in self.table if entry.type == type]
        for new_entry in new_table:
            if new_entry not in old_table:
                if new_entry.destination_router_id not in [entry.destination_router_id for entry in old_table]:
                    logger(f"add route {new_entry.destination_router_id} {new_entry.next_hop_router_id} {new_entry.cost}")
                else:
                    logger(f"update route {new_entry.destination_router_id} {new_entry.next_hop_router_id} {new_entry.cost}")
        for old_entry in old_table:
            if old_entry.destination_router_id not in [entry.destination_router_id for entry in new_table]:
                logger(f"remove route {old_entry.destination_router_id}")
        self.table = new_table

    def remove(self, type, router_id):
        self.table = [entry for entry in self.table if not (entry.type == type and entry.destination_router_id == router_id)]
        logger(f"remove route {router_id}")

class Neighbor:
    def __init__(self, router_id, cost):
        self.router_id = router_id
        self.cost = cost
        self.state = DOWN_STATE
        self.dbd = None
        self.last_seen = 0

    def update_state(self, new_state):
        old_state = self.state
        self.state = new_state
        if old_state != new_state:
            logger(f"Neighbor {self.router_id} state set to {new_state}")

    def update_dbd(self, dbd):
        self.dbd = dbd

class OSPFRouter:
    HELLO_INTERVAL = 1
    DBD_INTERVAL = 1
    DEAD_INTERVAL = 4 * HELLO_INTERVAL
    LSA_REFRESH_TIME = 15

    def __init__(self, router_id):
        self.router_id = router_id
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(("127.0.0.1", 10000 + router_id))
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.neighbors = []
        self.routing_table = RoutingTable()
        self.lsdb = LSDB(router_id)
        # topology is represented as adjacency list
        self.topology: dict[int, list[tuple[int, int]]] = {}

    def find_neighbor(self, router_id):
        for neighbor in self.neighbors:
            if neighbor.router_id == router_id:
                return neighbor
        return None

    def construct_topology(self):
        lsas = list(self.lsdb.lsas.values())
        # debug(f"LSAs: {lsas}")
        for lsa in lsas:
            self.topology[lsa.link_id] = []
            for neighbor in lsa.metrics:
                self.topology[lsa.link_id].append((neighbor, lsa.metrics[neighbor]))
        # debug(f"Topology: {self.topology}")

    def run_spf(self):
        if not any(neighbor.state == FULL_STATE for neighbor in self.neighbors):
            return
        self.construct_topology()
        # lsas = [lsa for lsa in self.lsdb.lsas.values() if lsa.link_id not in neighbors]

        # Dijkstra's algorithm
        visited = set()
        all_nodes = set()
        for router_id in self.topology:
            all_nodes.add(router_id)
            for neighbor, _ in self.topology[router_id]:
                all_nodes.add(neighbor)
        distance = {router_id: float("inf") for router_id in all_nodes}
        distance[self.router_id] = 0
        previous = {router_id: None for router_id in all_nodes}

        while len(visited) < len(self.topology):
            min_distance = float("inf")
            min_router_id = None
            for router_id in self.topology:
                if router_id not in visited and distance[router_id] < min_distance:
                    min_distance = distance[router_id]
                    min_router_id = router_id
            if min_router_id is None:
                break
            if min_router_id not in self.topology:
                continue
            visited.add(min_router_id)
            for neighbor, cost in self.topology[min_router_id]:
                if distance[min_router_id] + cost < distance[neighbor]:
                    distance[neighbor] = distance[min_router_id] + cost
                    previous[neighbor] = min_router_id

        new_routing_table = []
        for router_id in self.topology:
            if router_id == self.router_id:
                continue
            if distance[router_id] != float("inf"):
                next_hop = previous[router_id]  
                while previous[next_hop] != self.router_id and previous[next_hop] is not None:
                    next_hop = previous[next_hop]
                if next_hop == self.router_id:
                    next_hop = router_id
                new_routing_table.append(RoutingTableEntry(router_id, next_hop, distance[router_id], OSPF_ROUTE))

        self.routing_table.update(OSPF_ROUTE, new_routing_table)

    def send_hello(self, neighbor, already_seen=False, ack=False):
        hello_packet = HelloPacket(self.router_id, already_seen, ack)
        packet = OSPFPacket(self.router_id, neighbor.router_id, 1, 0, hello_packet)
        self.send_packet(packet)

    def send_hello_job(self):
        while True:
            for neighbor in self.neighbors:
                if neighbor.state == DOWN_STATE:
                    self.send_hello(neighbor)
                else:
                    self.send_hello(neighbor, already_seen=True)
            time.sleep(self.HELLO_INTERVAL)

    def send_dbd(self, neighbor):
        dbd_packet = DBD(self.router_id, 1, list(self.lsdb.lsas.values()))
        packet = OSPFPacket(self.router_id, neighbor.router_id, DBD_PACKET, 0, dbd_packet)
        self.send_packet(packet)

    def send_dbd_job(self):
        while True:
            for neighbor in self.neighbors:
                if neighbor.state == EXCHANGE_STATE or neighbor.state == FULL_STATE:
                    # debug(f"Send DBD to {neighbor.router_id}")
                    self.send_dbd(neighbor)
            time.sleep(self.DBD_INTERVAL)

    def check_lsa_job(self):
        while True:
            for lsa in self.lsdb.lsas.values():
                if time.time() - lsa.received_time > self.LSA_REFRESH_TIME:
                    lsa.received_time = time.time()
                    lsa.seq += 1
                    for neighbor in self.neighbors:
                        if neighbor.state == FULL_STATE:
                            self.send_lsu(neighbor.router_id, [lsa])
            time.sleep(1)

    def send_lsr(self, router_id, router_ids):
        lsr_packet = LSRPacket(router_ids)
        packet = OSPFPacket(self.router_id, router_id, LSR_PACKET, 0, lsr_packet)
        self.send_packet(packet)

    def send_lsu(self, router_id, lsas):
        lsu_packet = LSUPacket(lsas)
        packet = OSPFPacket(self.router_id, router_id, LSU_PACKET, 0, lsu_packet)
        self.send_packet(packet)

    def send_message(self, router_id, message):
        packet = OSPFPacket(self.router_id, router_id, TEXT_PACKET, len(message), message.encode())
        self.send_packet(packet)

    def find_route(self, router_id):
        candidate = []
        for entry in self.routing_table.table:
            if entry.destination_router_id == router_id:
                # return entry.next_hop_router_id
                candidate.append(entry)
        next_hop = -1
        # STATIC_ROUTE has higher priority
        sorted_candidate = sorted(candidate, key=lambda x: x.type)
        if sorted_candidate:
            next_hop = sorted_candidate[0].next_hop_router_id
        return next_hop

    def send_packet(self, packet):
        # debug(f"Send {packet.packet_type} packet to {packet.destination_router_id}")
        next_hop = self.find_route(packet.destination_router_id) if packet.packet_type == TEXT_PACKET else packet.destination_router_id
        self.udp_socket.sendto(
            pickle_bytes(packet),
            ("127.0.0.1", 10000 + next_hop)
        )

    def handle_packet(self, packet):
        # logger(f"Received packet from {packet.source_router_id}")
        if packet.destination_router_id != self.router_id:
            if packet.packet_type == TEXT_PACKET:
                logger(f"Forward message from {packet.source_router_id} to {packet.destination_router_id}: {packet.packet_data.decode()}")
            self.send_packet(packet)
            return
        pkt_info = OSPFPacketInfo(packet.source_router_id, packet.destination_router_id)
        if packet.packet_type == HELLO_PACKET:
            self.handle_hello_packet(packet.packet_data, pkt_info)
        elif packet.packet_type == DBD_PACKET:
            self.handle_dbd_packet(packet.packet_data, pkt_info)
        elif packet.packet_type == LSR_PACKET:
            self.handle_lsr_packet(packet.packet_data, pkt_info)
        elif packet.packet_type == LSU_PACKET:
            self.handle_lsu_packet(packet.packet_data, pkt_info)
        elif packet.packet_type == TEXT_PACKET:
            logger(f"Recv message from {packet.source_router_id}: {packet.packet_data.decode()}")

    def handle_command(self, command):
        cmds = command.split(" ")
        if cmds[0] == "addlink":
            neighbor_id = int(cmds[1])
            cost = int(cmds[2])
            neighbor = Neighbor(neighbor_id, cost)
            self.neighbors.append(neighbor)
            logger(f"add neighbor {neighbor_id} {cost}")
            # self.lsdb.add_lsa(LinkStateAdvertisement(self.router_id, 1, {neighbor_id: cost}, time.time()))
            self.lsdb.update_lsa(self.router_id, {neighbor_id: cost})
            self.routing_table.update(STATIC_ROUTE, self.routing_table.table + [RoutingTableEntry(neighbor_id, neighbor_id, cost, STATIC_ROUTE)])
            
        elif cmds[0] == "setlink":
            neighbor_id = int(cmds[1])
            cost = int(cmds[2])
            neighbor = self.find_neighbor(neighbor_id)
            if neighbor is not None:
                neighbor.cost = cost
                self.lsdb.update_lsa(self.router_id, {neighbor_id: cost})
                logger(f"update neighbor {neighbor_id} {cost}")
        elif cmds[0] == "rmlink":
            neighbor_id = int(cmds[1])
            self.neighbors = [n for n in self.neighbors if n.router_id != neighbor_id]
            
            # debug(f"Neighbors: {self.neighbors}")
            
            logger(f"remove neighbor {neighbor_id}")


            self.lsdb.remove_lsa(neighbor_id)
            self.lsdb.get_lsa(self.router_id).metrics = {k: v for k, v in self.lsdb.get_lsa(self.router_id).metrics.items() if k != neighbor_id}
            self.routing_table.remove(STATIC_ROUTE, neighbor_id)
            self.run_spf()
            
        elif cmds[0] == "send":
            router_id = int(cmds[1])
            msg = " ".join(cmds[2:])
            if router_id in range(1, 100):
                self.send_message(router_id, msg)
            else:
                print("Invalid router id")
        elif cmds[0] == "exit":
            sys.exit(0)

    def handle_hello_packet(self, packet, pkt_info):
        if packet.ack:
            return
        neighbor = self.find_neighbor(pkt_info.source_router_id)
        if neighbor is None:
            return
        if neighbor.state != FULL_STATE:
            # self.lsdb.update_lsa(self.router_id, {neighbor_id: cost})
            if packet.already_seen:
                neighbor.update_state(EXCHANGE_STATE)
            else:
                neighbor.update_state(INIT_STATE)
        self.send_hello(neighbor, already_seen=True, ack=True)

    def handle_dbd_packet(self, packet, pkt_info):
        # debug(f"Received DBD packet: {packet}")
        neighbor = self.find_neighbor(pkt_info.source_router_id)
        if neighbor is None:
            return

        dbd = packet
        neighbor.update_dbd(dbd)
        diff = []
        for lsa in dbd.link_state_advertisements:
            # if self.lsdb.get_lsa(lsa.link_id) != lsa:
            if self.lsdb.get_lsa(lsa.link_id) is None or self.lsdb.get_lsa(lsa.link_id).seq < lsa.seq:
                diff.append(lsa.link_id)
        # debug(f"DBD diff: {diff} from {neighbor.router_id}")

        # check if the neighbor is in the exchange state
        if diff:
            self.send_lsr(neighbor.router_id, diff)
        else:
            neighbor.update_state(FULL_STATE)
            self.run_spf()

    def handle_lsr_packet(self, packet, pkt_info):
        lsr = packet
        neighbor = self.find_neighbor(pkt_info.source_router_id)
        # debug(f"Received LSR packet: {lsr}")
        requested_lsas = []
        for lsa in lsr.request_router_ids:
            requested_lsa = self.lsdb.get_lsa(lsa)
            # debug(f"Requested LSA {lsa}, found {requested_lsa}")
            if requested_lsa is not None:
                requested_lsas.append(requested_lsa)
        if requested_lsas:
            self.send_lsu(neighbor.router_id, requested_lsas)

    def handle_lsu_packet(self, packet, pkt_info):
        lsu = packet
        neighbor = self.find_neighbor(pkt_info.source_router_id)
        # debug(f"Received LSU packet: {lsu}")
        updated_lsas = []
        for lsa in lsu.link_state_advertisements:
            existing_lsa = self.lsdb.get_lsa(lsa.link_id)
            if existing_lsa is None or lsa.seq > existing_lsa.seq:
                # self.lsdb.add_lsa(lsa)
                self.lsdb.update_lsa_on_basis(lsa.link_id, lsa.metrics)
                for neighbor in self.neighbors:
                    if neighbor.state == FULL_STATE:
                        self.send_lsu(neighbor.router_id, updated_lsas)

        self.run_spf()

    def udp_socket_job(self):
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
            packet = unpickle_bytes(data)
            self.handle_packet(packet)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ospf.py <router_id>")
        sys.exit(1)
    router_id = int(sys.argv[1])
    router = OSPFRouter(router_id)
    hello_thread = threading.Thread(target=router.send_hello_job, daemon=True)
    hello_thread.start()
    udp_thread = threading.Thread(target=router.udp_socket_job, daemon=True)
    udp_thread.start()
    dbd_thread = threading.Thread(target=router.send_dbd_job, daemon=True)
    dbd_thread.start()
    lsa_thread = threading.Thread(target=router.check_lsa_job, daemon=True)
    lsa_thread.start()
    while True:
        command = input("Enter a command: ")
        router.handle_command(command)

# NSCAP

## HW2
simulating ping from different devices, how the ARP table on the host and the MAC table on the switch change

+ The ARP table will map the destination IP to the destination MAC address.
+ The MAC table records which port to forward packets to for a particular destination host.

## HW3
calculate 'success_rate, idle_rate, collision_rate' when using different Medium Access Control protocol
, including ALOHA, slotted ALOHA, Carrier Sense Multiple Access (CSMA), and Carrier Sense Multiple Access with Collision Avoidance (CSMA/CA).

Observing the 'success_rate, idle_rate, collision_rate' of various MAC protocols, what changes can be expected as factors such as the number of packets per unit increases, the packet length increases, the number of devices increases, etc.

## HW4
Simulating the way OSPF routers exchange messages, including Hello messages, LSAs, DBDs, etc.

By checking which routers the packet passes through when being forwarded, we can verify if Dijkstra's algorithm is implemented correctly.


## HW5
Design and implement a pair of web client program and web server program that support the HTTP 1.0, HTTP 1.1, HTTP 2.0 protocols, respectively.

+ HTTP/1.0: Each request needs to create a new connection.
+ HTTP/1.1: The connection between the client the and server will be kept for a while and multiple requests/responses can be transferred over the same connection.
+ HTTP/2: A connection can have multiple streams to handle multiple requests and responses simultaneously. Each stream is used to transfer a pair of request and response.

## HW6
using mininet to create the network topology and implementing a ryu controller with some flow table entries.

Building GRE Tunnel between switches on different VMs
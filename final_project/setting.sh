#!/bin/bash

modprobe bonding

# Create bond0 interface and set MAC address
sudo ip link add bond0 type bond
sudo ip link set bond0 address 02:01:02:03:04:08

# Set physical interfaces down, set MAC address, and add to bond0
sudo ip link set h1-eth0 down
sudo ip link set h1-eth0 address 00:00:00:00:00:11
sudo ip link set h1-eth0 master bond0
sudo ip link set h1-eth1 down
sudo ip link set h1-eth1 address 00:00:00:00:00:12
sudo ip link set h1-eth1 master bond0

# Assign IP address to bond0 and delete from h1-eth0
sudo ip addr add 10.0.0.1/8 dev bond0
sudo ip addr del 10.0.0.1/8 dev h1-eth0

# Bring bond0 interface up
sudo ip link set bond0 up
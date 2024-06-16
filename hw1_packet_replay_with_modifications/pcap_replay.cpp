#include <arpa/inet.h> // inet_addr
#include <cstring>     // memcpy
#include <iostream>
#include <netinet/ether.h> // ethernet header struct
#include <netinet/ip.h>    // ip header struct
#include <netinet/udp.h>   // udp header struct
#include <pcap.h>          // pcap libary
#include <unistd.h>

#define MAX_PACKET_SIZE 65535
#define ETH_ALEN 6
#define ETH_HLEN 14
#define PCAP_ERRBUF_SIZE 256

/* some useful identifiers:
 * - ETH_ALEN = 6   (ethernet address length)
 * - ETH_HLEN = 14	(ethernet header length)
*/

// TODO 5
void modify_mac_address(struct ether_header *eth_header) {
    // struct ether_header reference:
    // https://sites.uclouvain.be/SystInfo/usr/include/net/ethernet.h.html

    // modify the source mac address to '08:00:12:34:56:78'
    u_int8_t new_source_mac[ETH_ALEN] = {0x08, 0x00, 0x12, 0x34, 0x56, 0x78};
    memcpy(eth_header->ether_shost, new_source_mac, ETH_ALEN);

    // modify the destination mac address to '08:00:12:34:ac:c2'
    u_int8_t new_dest_mac[ETH_ALEN] = {0x08, 0x00, 0x12, 0x34, 0xac, 0xc2};
    memcpy(eth_header->ether_dhost, new_dest_mac, ETH_ALEN);
    
}

// TODO 6
void modify_ip_address(struct ip *ip_header) {
    // modify the source ip address to '10.1.1.3'
    ip_header->ip_src.s_addr = inet_addr("10.1.1.3");
    
    // modify the destination ip address to '10.1.1.4'
    ip_header->ip_dst.s_addr = inet_addr("10.1.1.4");
}

int main() {

    // TODO 1: Open the pcap file
    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t *handle = pcap_open_offline("test.pcap", errbuf);
    if (handle == NULL) {
        std::cerr << "Error: " << errbuf << std::endl;
        return 1;
    }

    // TODO 2: Open session with loopback interface "lo"
    pcap_t *send_handle = pcap_open_live("lo", BUFSIZ, 1, 1000, errbuf);
    if (send_handle == NULL) {
        std::cerr << "Error: " << errbuf << std::endl;
        return 1;
    }


    struct pcap_pkthdr *header;
    const u_char *packet;

    // TODO 8: Variables to store the time difference between each packet
    struct timeval prev_packet_time = {0, 0};
    struct timeval current_packet_time;


    // TODO 3: Loop through each packet in the pcap file
    while (pcap_next_ex(handle, &header, &packet) >= 0){

        // TODO 4: Send the original packet
        pcap_sendpacket(send_handle, packet, header->len);


        // TODO 5: Modify mac address (function up above)
        struct ether_header *eth_header = (struct ether_header *)packet;
        modify_mac_address(eth_header);

        // TODO 6: Modify ip address if it is a IP packet (hint: ether_type)
        if (eth_header->ether_type == htons(ETHERTYPE_IP)) {
            // Assuming Ethernet headers
            struct ip *ip_header = (struct ip *)(packet + ETH_HLEN);
            modify_ip_address(ip_header);   // modify function up above
        }

        // TODO 8: Calculate the time difference between the current and the
        // previous packet and sleep. (hint: usleep)
        current_packet_time = header->ts;
        if (prev_packet_time.tv_sec != 0) {
            long sec_diff = current_packet_time.tv_sec - prev_packet_time.tv_sec;
            long usec_diff = current_packet_time.tv_usec - prev_packet_time.tv_usec;
            long total_diff = sec_diff * 1000000 + usec_diff;
            usleep(total_diff);
        }

        // TODO 7: Send the modified packet
        pcap_sendpacket(send_handle, packet, header->len);


        // TODO 8: Update the previous packet time
        prev_packet_time = current_packet_time;
    }

    // Close the pcap file
    pcap_close(handle);
    pcap_close(send_handle);
    
    return 0;
}
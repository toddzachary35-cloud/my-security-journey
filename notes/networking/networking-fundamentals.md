# Networking Fundamentals

Notes built while working through Cisco Networking Academy and Security+ prep. Living document, updated as I go.

## The OSI Model

Seven layers, top to bottom. Mnemonic: **A**ll **P**eople **S**eem **T**o **N**eed **D**ata **P**rocessing.

| Layer | Name | What it does | Examples |
|---|---|---|---|
| 7 | Application | Interface for user-facing software | HTTP, FTP, DNS, SSH |
| 6 | Presentation | Formats/encrypts/compresses data | SSL/TLS, JPEG, ASCII |
| 5 | Session | Opens, manages, closes sessions between hosts | NetBIOS, RPC |
| 4 | Transport | End-to-end delivery, reliability | TCP, UDP |
| 3 | Network | Logical addressing, routing between networks | IP, ICMP, routers |
| 2 | Data Link | Physical addressing within a local network | MAC addresses, switches, ARP |
| 1 | Physical | Actual transmission of raw bits | Cables, radio, hubs |

**Why it matters practically:** when troubleshooting or attacking something, thinking "what layer is this problem at" narrows things down fast. A DNS issue is layer 7. A MAC spoofing attack is layer 2. Understanding which layer a tool operates at (Wireshark shows you almost all of them, Nmap mostly works at 3/4) makes the tools make more sense.

## TCP vs UDP

| | TCP | UDP |
|---|---|---|
| Connection | Connection-oriented (handshake) | Connectionless |
| Reliability | Guaranteed delivery, ordered | No guarantee, no order |
| Speed | Slower (overhead from reliability) | Faster |
| Used for | Web (HTTP/HTTPS), SSH, FTP, email | DNS, streaming, VoIP, DHCP |

**TCP three-way handshake:** SYN → SYN-ACK → ACK. This is what a SYN scan (`nmap -sS`) is abusing/leveraging, it sends the SYN and reads the response without ever completing the handshake, which is why it's "stealthier" than a full connect scan.

## IP Addressing & Subnetting

- **IPv4** address = 32 bits, written as four octets (e.g. `192.168.1.10`)
- **Subnet mask** defines which portion of the address is the network vs. the host (e.g. `255.255.255.0` = /24, first 24 bits are network)
- **CIDR notation** (`/24`, `/16`, etc.) is shorthand for the subnet mask

Quick reference for common CIDR blocks:

| CIDR | Subnet Mask | Usable Hosts |
|---|---|---|
| /24 | 255.255.255.0 | 254 |
| /25 | 255.255.255.128 | 126 |
| /26 | 255.255.255.192 | 62 |
| /27 | 255.255.255.224 | 30 |
| /28 | 255.255.255.240 | 14 |

**Private IP ranges** (non-routable on the public internet, used internally):
- `10.0.0.0 – 10.255.255.255` (10.0.0.0/8)
- `172.16.0.0 – 172.31.255.255` (172.16.0.0/12)
- `192.168.0.0 – 192.168.255.255` (192.168.0.0/16)

## Common Ports (quick recall list)

See `common-ports-services-reference.md` for the full breakdown, quick recall list here:

- **21** FTP
- **22** SSH
- **23** Telnet
- **25** SMTP
- **53** DNS
- **80** HTTP
- **110** POP3
- **143** IMAP
- **443** HTTPS
- **445** SMB
- **3389** RDP

## Key Networking Devices

| Device | Layer | Function |
|---|---|---|
| Hub | 1 | Broadcasts to all ports, no intelligence |
| Switch | 2 | Forwards based on MAC address, per-port |
| Router | 3 | Forwards based on IP address, connects networks |
| Firewall | 3/4 (up to 7 for NGFW) | Filters traffic based on rules |

## DNS Basics

- Translates domain names into IP addresses
- **Record types worth knowing:** `A` (IPv4 address), `AAAA` (IPv6), `CNAME` (alias), `MX` (mail server), `TXT` (arbitrary text, often used for verification/SPF)
- Relevant to my own setup: Pi-hole on the home server works by acting as the DNS resolver for my devices and blocking lookups to known ad/tracker domains before they resolve

## Notes to Self / Things to Revisit

- [ ] Practice subnetting by hand until it's fast, not just recognizable
- [ ] Go deeper on ARP and how ARP spoofing/poisoning actually works at layer 2
- [ ] Understand NAT properly, why private IPs need it to reach the internet

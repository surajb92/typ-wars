OUTLINE | WIP Notes
===================

To do:
1. Go to new window
    a. Load for 3 seconds "Checking servers" (put "loading, 3,2,1 if you want"). [LATER]
        i. Popup message
        ii. 3 second wait while it searches server
        iii. Set this system to client if no other server
        iv. Move to server selection frame if there is already a server in the network
2. Figure out how networking works = Result : Too complicated to do over internet (NAT Tunneling etc.). Try with just over local network for now.
    a. Socket programming : Simple client - server connection with localhost [DONE]
    b. Send multicast to local network with server's IP. [WIP]
        [Note : ^ Works when ip addr add with multicast address, but that's likely not the right way to code it for wider use]

STATUS
======

Things adjusted :
    Added ip_forwarding with "sysctl net.ipv4.ip_forward=1" change to 0 if any issues. Test with "cat /proc/sys/net/ipv4/ip_forward". [CHANGED TO 0]
Multicast on pause.
Trying with broadcast.
Testing UDP data streaming in general.

Testing with TCP DUMP
Both laptops receive multicast packets, i.e. Router has no issues.
2nd test laptop only receives TCP dump when ciient is registered

TCPdump on source laptop shows dump no matter if client is running or not
TCPdump on destination laptop ONLY shows dump if the client is running (i.e. Mcast address is registered)

Potential issues are all within Python only.
Things to check -
1. Whether the current method of 4sl registration (INADDR_ANY) causes issues when reading traffic. [Switched to local interface binding and nothing changed]
2. recv something wrong maybe? [recv is TCP, recvfrom is UDP]
3. ip route show table local --> This seems to be the problem. No routing of multicast packets. Could be a red herring though.

netstat shows both clients register to the multicast address, so no issue there either.

BROADCAST TEST
==============
Socat tested : Broadcast is working locally.
TCPdump tested : Broadcast is being sent over local internet.
Seems to be some bottleneck in app layer with both broadcast and multicast.

UDP with host tested.
Roles are reversed in UDP.
The server is the one sending packets advertising themselves, while the client is the one that listens to said packets.
Setting UDP terminology as LISTENER and SENDER for ease of documentation.
If no bind on listener side, can still run program, but will not receive data.

NEXT STEPS
==========
Troubleshoot what is happening at app layer, whether linux blocks multicast/broadcast and if so, whether something about it can be done within python.

Useful
======
TCP dump :
sudo tcpdump -i wlan0 -s0 -vv net 224.0.0.0/4
sudo tcpdump -i eth0 -n udp
all UDP packets

!! Python code to get public IP !!
import socket
hostname = socket.getfqdn()
print("IP Address:",socket.gethostbyname_ex(hostname)[2][1])

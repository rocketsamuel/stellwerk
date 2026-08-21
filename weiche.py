
import socket
import time

Z21_IP = "192.168.178.223"
Z21_PORT = 21105

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Alternative DCC Command Structs für Weiche 5
# Header 0x53 (LAN_X_SET_TURNOUT mit DCC-Bit)
cmds = [
    ("DCC Direct (Addr 4, Turn ON)",  b'\x09\x00\x40\x00\x53\x00\x04\x89\xfe'),
    ("DCC Direct (Addr 4, Turn OFF)", b'\x09\x00\x40\x00\x53\x00\x04\x81\xf6'),
    ("DCC Direct (Addr 0, Turn ON)",  b'\x09\x00\x40\x00\x53\x00\x00\x89\xfa'),
    ("DCC Direct (Addr 0, Turn OFF)", b'\x09\x00\x40\x00\x53\x00\x00\x81\xf2'),
]

for name, pkt in cmds:
    print(f"Sende: {name}")
    sock.sendto(pkt, (Z21_IP, Z21_PORT))
    time.sleep(0.3)

sock.close()

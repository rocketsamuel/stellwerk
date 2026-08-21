#!/bin/bash

# Konfiguration
Z21_IP="192.168.178.223"
Z21_PORT="21105"

WEICHE=$1
STELLUNG=$2

if [ -z "$WEICHE" ] || [ -z "$STELLUNG" ]; then
    echo "Nutzung: $0 <Weichennummer> <straight|turnout>"
    exit 1
fi

# Adresse berechnen (0-basiert)
ADDR_DEC=$((WEICHE - 1))
ADDR_HEX=$(printf "%02x" $ADDR_DEC)

# Stellung festlegen (0x89 = Abzweig, 0x88 = Gerade)
if [ "$STELLUNG" == "turnout" ] || [ "$STELLUNG" == "a" ]; then
    CMD_ON="89"
    CMD_OFF="81"
elif [ "$STELLUNG" == "straight" ] || [ "$STELLUNG" == "g" ]; then
    CMD_ON="88"
    CMD_OFF="80"
else
    echo "Fehler: Stellung muss 'straight' oder 'turnout' sein."
    exit 1
fi

# XOR / Prüfsumme berechnen (Python Hilfsskript)
python3 -c "
import socket, time

ip = '$Z21_IP'
port = $Z21_PORT
addr = 0x$ADDR_HEX
cmd_on = 0x$CMD_ON
cmd_off = 0x$CMD_OFF

# Paket zusammenbauen: Length(2) + Header(2) + XHeader(2) + Addr(1) + Cmd(1) + XOR(1)
xor_on = 0x40 ^ 0x00 ^ 0x53 ^ 0x00 ^ addr ^ cmd_on
xor_off = 0x40 ^ 0x00 ^ 0x53 ^ 0x00 ^ addr ^ cmd_off

pkt_on = bytes([0x09, 0x00, 0x40, 0x00, 0x53, 0x00, addr, cmd_on, xor_on])
pkt_off = bytes([0x09, 0x00, 0x40, 0x00, 0x53, 0x00, addr, cmd_off, xor_off])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Spule EIN
sock.sendto(pkt_on, (ip, port))
time.sleep(0.2)
# Spule AUS
sock.sendto(pkt_off, (ip, port))
sock.close()
"

echo "Weiche $WEICHE auf $STELLUNG geschaltet."

import socket
import struct

Z21_IP = "192.168.178.223"
Z21_PORT = 21105

# Socket erstellen und an lokalen Port binden
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", 0)) # Automatischen lokalen Port wählen
sock.settimeout(10.0)

try:
    # 1. Bei der Z21 für Weichen-Broadcasts anmelden (LAN_SET_BROADCASTFLAGS)
    # Flag 0x00000001 = Weichen- und Zubehörzustände empfangen
    broadcast_cmd = b'\x08\x00\x50\x00\x01\x00\x00\x00'
    sock.sendto(broadcast_cmd, (Z21_IP, Z21_PORT))
    
    print("Lausche auf Weichen-Schaltvorgänge... (Strg+C zum Beenden)\n")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            
            # Prüfen ob es ein X-Bus Paket ist (Header 0x40 0x00)
            if len(data) >= 7 and data[2] == 0x40 and data[3] == 0x00:
                xheader = data[4]
                
                # 0x43 oder 0x53 = Turnout Info / Information über Weichenstellung
                if xheader in (0x43, 0x53):
                    addr_msb = data[5]
                    addr_lsb = data[6]
                    
                    # Adresse berechnen (+1 für 1-basierte Anzeige)
                    weiche_nr = (addr_msb * 256 + addr_lsb) + 1
                    
                    # Zustand aus Byte 7 auslesen (falls vorhanden)
                    if len(data) >= 8:
                        zustand_byte = data[7]
                        
                        # Bit 0/1 auswerten: 1 = Gerade, 2 = Abzweig
                        stellung_bit = zustand_byte & 0x03
                        if stellung_bit == 1:
                            stellung = "GERADE"
                        elif stellung_bit == 2:
                            stellung = "ABZWEIG"
                        else:
                            stellung = f"Unbekannt / Impuls (0x{zustand_byte:02x})"
                        
                        print(f"-> Weiche {weiche_nr} wurde geschaltet auf: {stellung}")
                    else:
                        print(f"-> Weiche {weiche_nr} wurde betätigt.")
                        
        except socket.timeout:
            # Re-Abonnement senden, falls länger nichts passiert (Keep-Alive)
            sock.sendto(broadcast_cmd, (Z21_IP, Z21_PORT))

except KeyboardInterrupt:
    print("\nBeendet.")
finally:
    sock.close()

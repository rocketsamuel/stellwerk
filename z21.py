import socket
import threading
import time

from config import (
    Z21_IP,
    Z21_PORT,
    TURNOUT_PULSE_TIME,
    BROADCAST_KEEPALIVE,
    Z21_BROADCAST_FLAGS,
)


class Z21:

    def __init__(self):

        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        self.socket.bind(("", 0))
        self.socket.settimeout(1.0)

        self.running = False
        self.thread = None

        self.callback = None
        self.broadcast_callback = None

        # Z21-Adresse -> Stellung
        self.states = {}

    def subscribe(self):

        flags = Z21_BROADCAST_FLAGS.to_bytes(
            4,
            byteorder="little"
        )

        packet = bytes([
            0x08,
            0x00,
            0x50,
            0x00,
        ]) + flags

        self.socket.sendto(
            packet,
            (Z21_IP, Z21_PORT)
        )

    def set_turnout(
        self,
        address,
        position
    ):

        if position == "straight":

            cmd_on = 0x88
            cmd_off = 0x80

        elif position == "turnout":

            cmd_on = 0x89
            cmd_off = 0x81

        else:

            raise ValueError(
                f"Ungültige Stellung: {position}"
            )

        # Z21-Adresse 1-basiert
        # X-Bus-Adresse 0-basiert

        address -= 1

        msb = (address >> 8) & 0xff
        lsb = address & 0xff

        xor_on = (
            0x40 ^
            0x00 ^
            0x53 ^
            msb ^
            lsb ^
            cmd_on
        )

        xor_off = (
            0x40 ^
            0x00 ^
            0x53 ^
            msb ^
            lsb ^
            cmd_off
        )

        packet_on = bytes([
            0x09,
            0x00,
            0x40,
            0x00,
            0x53,
            msb,
            lsb,
            cmd_on,
            xor_on,
        ])

        packet_off = bytes([
            0x09,
            0x00,
            0x40,
            0x00,
            0x53,
            msb,
            lsb,
            cmd_off,
            xor_off,
        ])

        self.socket.sendto(
            packet_on,
            (Z21_IP, Z21_PORT)
        )

        time.sleep(TURNOUT_PULSE_TIME)

        self.socket.sendto(
            packet_off,
            (Z21_IP, Z21_PORT)
        )

    def start(
        self,
        callback,
        broadcast_callback=None
    ):

        self.callback = callback
        self.broadcast_callback = broadcast_callback
        self.running = True

        self.subscribe()

        self.thread = threading.Thread(
            target=self._listener,
            daemon=True
        )

        self.thread.start()

    def _listener(self):

        last_subscription = time.monotonic()

        while self.running:

            if (
                time.monotonic() -
                last_subscription
                >= BROADCAST_KEEPALIVE
            ):

                try:
                    self.subscribe()
                except OSError:
                    pass

                last_subscription = time.monotonic()

            try:

                data, _ = self.socket.recvfrom(1024)

            except socket.timeout:

                continue

            except OSError:

                break

            self._process_datagram(data)

    def _process_datagram(self, data):

        """Zerlegt ein UDP-Datagramm in Z21-Datasets.

        Die Z21 darf mehrere Datasets in einem einzigen
        UDP-Datagramm zusammenfassen.
        """

        offset = 0

        while offset + 4 <= len(data):

            length = int.from_bytes(
                data[offset:offset + 2],
                byteorder="little"
            )

            if length < 4 or offset + length > len(data):
                # Auch fehlerhafte/unvollständige Daten sichtbar
                # machen, statt sie still zu verwerfen.
                if self.broadcast_callback:
                    self.broadcast_callback(data[offset:])
                return

            dataset = data[offset:offset + length]

            if self.broadcast_callback:
                self.broadcast_callback(dataset)

            self._process(dataset)
            offset += length

    def _process(self, data):

        if len(data) < 8:
            return

        if data[2] != 0x40:
            return

        if data[3] != 0x00:
            return

        if data[4] not in (0x43, 0x53):
            return

        address = (
            (data[5] << 8)
            | data[6]
        ) + 1

        state = data[7] & 0x03

        if state == 1:

            position = "straight"

        elif state == 2:

            position = "turnout"

        else:

            return

        self.states[address] = position

        if self.callback:

            self.callback(
                address,
                position
            )

    def get_state(self, address):

        return self.states.get(address)

    def stop(self):

        self.running = False

        try:
            self.socket.close()
        except OSError:
            pass

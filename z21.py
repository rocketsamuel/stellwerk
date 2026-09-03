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
        self.feedback_callback = None
        self.extended_accessory_callback = None

        # Z21-Adresse -> Stellung
        self.states = {}

        # (R-Bus-Modul, Eingang) -> belegt/frei
        self.feedback_states = {}

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

    def request_feedback_status(self, group):

        if group not in (0, 1):
            raise ValueError(
                f"Ungültige R-Bus-Gruppe: {group}"
            )

        packet = bytes([
            0x05,
            0x00,
            0x81,
            0x00,
            group,
        ])

        self.socket.sendto(
            packet,
            (Z21_IP, Z21_PORT)
        )

    def request_turnout_info(self, address):

        function_address = address - 1
        msb = (function_address >> 8) & 0xff
        lsb = function_address & 0xff
        xor_byte = 0x43 ^ msb ^ lsb

        packet = bytes([
            0x08, 0x00, 0x40, 0x00,
            0x43, msb, lsb, xor_byte,
        ])

        self.socket.sendto(packet, (Z21_IP, Z21_PORT))

    def request_extended_accessory_info(self, raw_address):

        msb = (raw_address >> 8) & 0xff
        lsb = raw_address & 0xff
        xor_byte = 0x44 ^ msb ^ lsb

        packet = bytes([
            0x09, 0x00, 0x40, 0x00,
            0x44, msb, lsb, 0x00, xor_byte,
        ])

        self.socket.sendto(packet, (Z21_IP, Z21_PORT))

    def start(
        self,
        callback,
        broadcast_callback=None,
        feedback_callback=None,
        extended_accessory_callback=None
    ):

        self.callback = callback
        self.broadcast_callback = broadcast_callback
        self.feedback_callback = feedback_callback
        self.extended_accessory_callback = extended_accessory_callback
        self.running = True

        self.subscribe()

        # Aktuellen Zustand beider R-Bus-Stränge abfragen.
        self.request_feedback_status(0)
        self.request_feedback_status(1)

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

        if len(data) >= 15 and data[2:4] == bytes([
            0x80,
            0x00,
        ]):
            self._process_feedback(data)
            return

        if len(data) < 8:
            return

        if data[2] != 0x40:
            return

        if data[3] != 0x00:
            return

        if data[4] == 0x44:
            self._process_extended_accessory(data)
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

    def _process_extended_accessory(self, data):

        if len(data) < 10 or data[8] != 0x00:
            return

        raw_address = (data[5] << 8) | data[6]
        value = data[7]

        if self.extended_accessory_callback:
            self.extended_accessory_callback(raw_address, value)

    def _process_feedback(self, data):

        group = data[4]

        if group not in (0, 1):
            return

        first_module = 1 + group * 10

        # Die zehn Statusbytes gehören aufsteigend zu den
        # R-Bus-Modulen. Jedes Bit steht für einen Eingang.
        for module_offset, status in enumerate(data[5:15]):

            module = first_module + module_offset

            for bit in range(8):

                input_number = bit + 1
                occupied = bool(status & (1 << bit))
                key = (module, input_number)
                previous = self.feedback_states.get(key)

                self.feedback_states[key] = occupied

                # Beim ersten Gesamtstatus freie Eingänge nicht
                # einzeln ausgeben. Bereits belegte Eingänge werden
                # dagegen sofort gemeldet.
                if previous is None and not occupied:
                    continue

                if (
                    previous is not None
                    and previous == occupied
                ):
                    continue

                if self.feedback_callback:
                    self.feedback_callback(
                        module,
                        input_number,
                        occupied
                    )

    def get_feedback_state(
        self,
        module,
        input_number
    ):

        return self.feedback_states.get(
            (module, input_number)
        )

    def get_state(self, address):

        return self.states.get(address)

    def stop(self):

        self.running = False

        try:
            self.socket.close()
        except OSError:
            pass

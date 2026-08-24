import os
import time
import threading

from config import (
    LED_COUNT,
    LED_BRIGHTNESS,
    BLINK_INTERVAL,
    ROUTE_MIN_BLINK_TIME,
    SWITCH_LEDS,
    ROUTE_LEDS,
)


DEVICE = "/dev/ws281x_pwm"


class LEDController:
    """
    WS2812B-Ansteuerung über den eigenen RP1-PWM-Kerneltreiber.

    Der Kernel-Treiber übernimmt:
        User memory -> DMA -> RP1 PWM FIFO

    Dieser Python-Treiber erzeugt deshalb den eigentlichen
    WS2812B-PWM-Bitstrom.

    WS2812B:
        0 -> 100
        1 -> 110

    Der RP1-PWM-Kanal arbeitet im MSBS-Modus und serialisiert
    die FIFO-Wörter MSB-first.
    """

    def __init__(
        self,
        count=LED_COUNT,
        brightness=LED_BRIGHTNESS,
        device=DEVICE,
    ):
        self.count = count
        self.brightness = max(0, min(255, brightness))
        self.device = device

        self.pixels = [
            (0, 0, 0)
            for _ in range(self.count)
        ]

        self.lock = threading.RLock()

        self._fd = None

        # Blink-Verwaltung
        self._blink_thread = None
        self._blink_stop = threading.Event()
        self._blink_callback = None

    # =========================================================
    # DEVICE
    # =========================================================

    def begin(self):
        """
        Öffnet den RP1-PWM-Treiber.
        """

        with self.lock:

            if self._fd is not None:
                return

            print(
                f"Öffne {self.device} ..."
            )

            self._fd = os.open(
                self.device,
                os.O_WRONLY
            )

            print(
                "WS281x PWM Device geöffnet."
            )

    def close(self):
        """
        Stoppt Blinkbetrieb, schaltet LEDs aus
        und schließt das Device.
        """

        self.stop_blink()

        with self.lock:

            if self._fd is None:
                return

            try:
                self.clear()
            finally:
                os.close(self._fd)
                self._fd = None

    # =========================================================
    # BRIGHTNESS
    # =========================================================

    def set_brightness(self, brightness):
        self.brightness = max(
            0,
            min(255, int(brightness))
        )

    def _apply_brightness(self, value):
        return (
            value * self.brightness
        ) // 255

    # =========================================================
    # PIXEL
    # =========================================================

    def set_pixel(
        self,
        index,
        r,
        g,
        b,
    ):
        if not 0 <= index < self.count:
            raise IndexError(
                f"LED-Index außerhalb des Bereichs: "
                f"{index}"
            )

        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))

        with self.lock:

            self.pixels[index] = (
                self._apply_brightness(r),
                self._apply_brightness(g),
                self._apply_brightness(b),
            )

    def set_pixel_rgb(
        self,
        index,
        rgb,
    ):
        r, g, b = rgb

        self.set_pixel(
            index,
            r,
            g,
            b,
        )

    def get_pixel(self, index):
        return self.pixels[index]

    def clear_pixels(self):
        with self.lock:
            for i in range(self.count):
                self.pixels[i] = (
                    0,
                    0,
                    0,
                )

    # =========================================================
    # WS2812B ENCODING
    # =========================================================

    @staticmethod
    def _encode_bit(bit):
        """
        WS2812B:

            0 = 100
            1 = 110
        """

        if bit:
            return 0b110

        return 0b100

    @classmethod
    def _encode_byte(cls, value):
        """
        Kodiert ein Byte in 24 PWM-Bits.
        """

        result = 0

        for bit in range(7, -1, -1):

            result <<= 3

            result |= cls._encode_bit(
                (value >> bit) & 1
            )

        return result

    def _build_bitstream(self):
        """
        Erzeugt den kompletten WS2812B-Bitstrom.

        WS2812B erwartet GRB, nicht RGB.
        """

        bits = []

        with self.lock:
            pixels = list(self.pixels)

        for r, g, b in pixels:

            # WS2812B: G R B
            for value in (
                g,
                r,
                b,
            ):

                for bit in range(7, -1, -1):

                    if (value >> bit) & 1:
                        bits.extend((1, 1, 0))
                    else:
                        bits.extend((1, 0, 0))

        return bits

    @staticmethod
    def _pack_words(bits):
        """
        Packt den seriellen PWM-Bitstrom MSB-first
        in 32-Bit-Wörter.

        Das letzte Wort wird mit 0 aufgefüllt.
        """

        # Reset-Zeit:
        #
        # WS2812B benötigt nach dem Datenstrom eine
        # LOW-Zeit von > 50 us.
        #
        # Bei 800 kHz:
        #   1 Bit = 1.25 us
        #
        # 64 Low-Bits entsprechen 26.7 us bei 2.4 MHz.
        # Wir verwenden großzügig 128 Low-Bits.
        bits = list(bits)

        bits.extend(
            [0] * 128
        )

        # Auf 32 Bit auffüllen
        remainder = len(bits) % 32

        if remainder:
            bits.extend(
                [0] * (32 - remainder)
            )

        data = bytearray()

        for offset in range(
            0,
            len(bits),
            32,
        ):

            word = 0

            for bit in bits[
                offset:offset + 32
            ]:

                word <<= 1
                word |= bit

            # big endian:
            # erster serieller Bit landet
            # im MSB des PWM-FIFO-Wortes.
            data.extend(
                word.to_bytes(
                    4,
                    byteorder="big"
                )
            )

        return bytes(data)

    def _build_frame(self):
        bits = self._build_bitstream()

        return self._pack_words(bits)

    # =========================================================
    # SHOW
    # =========================================================

    def show(self):
        """
        Überträgt den aktuellen LED-Zustand.
        """

        with self.lock:

            if self._fd is None:
                self.begin()

            data = self._build_frame()

            total = len(data)
            written_total = 0

            while written_total < total:

                written = os.write(
                    self._fd,
                    data[written_total:]
                )

                if written <= 0:
                    raise RuntimeError(
                        "WS281x PWM: "
                        "Schreiben fehlgeschlagen"
                    )

                written_total += written

    # =========================================================
    # EINFACHE FARBEN
    # =========================================================

    def set_all(
        self,
        r,
        g,
        b,
        show=True,
    ):
        for i in range(self.count):

            self.set_pixel(
                i,
                r,
                g,
                b,
            )

        if show:
            self.show()

    def off(self, show=True):
        self.clear_pixels()

        if show:
            self.show()

    def clear(self):
        self.clear_pixels()
        self.show()

    # =========================================================
    # LED INDEX
    # =========================================================

    def set_led(
        self,
        led,
        rgb,
        show=True,
    ):
        """
        Komfortfunktion für das Stellwerk.
        """

        self.set_pixel_rgb(
            led,
            rgb,
        )

        if show:
            self.show()

    # =========================================================
    # LED-MAPPING
    # =========================================================

    def set_leds(
        self,
        leds,
        rgb,
        show=True,
    ):
        """
        Setzt mehrere LED-Indizes gleichzeitig.
        """

        for led in leds:

            self.set_pixel_rgb(
                led,
                rgb,
            )

        if show:
            self.show()

    def set_switch_led(
        self,
        switch_name,
        position,
        rgb,
        show=True,
    ):
        """
        Setzt die LED einer Weichenstellung.
        """

        mapping = SWITCH_LEDS.get(
            switch_name,
            {}
        )

        led = mapping.get(position)

        if led is None:
            return

        self.set_pixel_rgb(
            led,
            rgb,
        )

        if show:
            self.show()

    # =========================================================
    # ROUTEN
    # =========================================================

    def set_route_leds(
        self,
        route_name,
        rgb,
        show=True,
    ):
        leds = ROUTE_LEDS.get(
            route_name,
            []
        )

        for led in leds:

            self.set_pixel_rgb(
                led,
                rgb,
            )

        if show:
            self.show()

    def clear_route(
        self,
        route_name,
        show=True,
    ):
        self.set_route_leds(
            route_name,
            (0, 0, 0),
            show=show,
        )

    # =========================================================
    # BLINKEN
    # =========================================================

    def start_blink(
        self,
        callback,
        interval=BLINK_INTERVAL,
    ):
        """
        Allgemeiner Blinkmechanismus.

        callback(visible) wird abwechselnd mit
        True / False aufgerufen.
        """

        self.stop_blink()

        self._blink_stop.clear()
        self._blink_callback = callback

        def worker():

            visible = True

            while not self._blink_stop.wait(
                interval
            ):

                visible = not visible

                try:
                    callback(visible)

                except Exception as exc:

                    print(
                        "WS281x Blinkfehler:",
                        exc
                    )

                    break

        self._blink_thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        self._blink_thread.start()

    def stop_blink(self):
        self._blink_stop.set()

        thread = self._blink_thread

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(
                timeout=1.0
            )

        self._blink_thread = None
        self._blink_callback = None

    # =========================================================
    # ROUTE BLINK
    # =========================================================

    def blink_route(
        self,
        route_name,
        rgb,
        interval=BLINK_INTERVAL,
    ):
        """
        Lässt die LEDs einer Fahrstraße blinken.
        """

        leds = list(
            ROUTE_LEDS.get(
                route_name,
                []
            )
        )

        if not leds:
            return

        def update(visible):

            with self.lock:

                if visible:

                    for led in leds:

                        self.set_pixel_rgb(
                            led,
                            rgb,
                        )

                else:

                    for led in leds:

                        self.set_pixel_rgb(
                            led,
                            (0, 0, 0),
                        )

            self.show()

        update(True)

        self.start_blink(
            update,
            interval=interval,
        )

    # =========================================================
    # CLEANUP
    # =========================================================

    def shutdown(self):
        self.close()

    def __enter__(self):
        self.begin()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.close()
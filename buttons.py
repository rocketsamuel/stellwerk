from gpiozero import Device
from gpiozero.pins.lgpio import LGPIOFactory

# ---------------------------------------------------------
# GPIO-Backend fest auf lgpio setzen
# ---------------------------------------------------------

Device.pin_factory = LGPIOFactory()

from gpiozero import Button


class Buttons:

    def __init__(
        self,
        button_pins,
        callback
    ):
        """
        button_pins:
            Dictionary mit Namen und BCM-GPIO-Nummern.

        Beispiel:

            {
                "RELEASE": 17,
                "HBF4": None,
                "ABS1": None,
            }

        callback:
            Funktion, die bei einem Tastendruck
            mit dem Namen des Tasters aufgerufen wird.
        """

        self.callback = callback
        self.buttons = {}

        # -------------------------------------------------
        # Taster anlegen
        # -------------------------------------------------

        for name, gpio in button_pins.items():

            # None bedeutet:
            # Dieser Taster ist noch nicht angeschlossen.
            if gpio is None:
                continue

            print(
                f"Taster {name}: "
                f"GPIO {gpio}"
            )

            button = Button(
                gpio,
                pull_up=True,
                bounce_time=0.05
            )

            button.when_pressed = (
                lambda name=name:
                self._pressed(name)
            )

            self.buttons[name] = button

        print(
            f"{len(self.buttons)} Taster aktiviert."
        )

    # =====================================================
    # TASTER GEDRÜCKT
    # =====================================================

    def _pressed(
        self,
        name
    ):

        print(
            f"Taster gedrückt: {name}"
        )

        if self.callback:

            self.callback(name)

    # =====================================================
    # SCHLIESSEN
    # =====================================================

    def close(self):

        for button in self.buttons.values():

            button.close()

        self.buttons.clear()

        print(
            "Taster geschlossen."
        )
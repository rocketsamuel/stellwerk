from gpiozero import Button
from gpiozero.pins.lgpio import LGPIOFactory


class Buttons:

    def __init__(
        self,
        button_pins,
        callback
    ):

        self.callback = callback
        self.buttons = {}

        # Raspberry Pi 5:
        # Die normalen GPIOs liegen bei unserem Setup auf gpiochip15.
        pin_factory = LGPIOFactory(chip=15)

        # -------------------------------------------------
        # Taster einrichten
        # -------------------------------------------------

        for name, pin in button_pins.items():

            # Nicht belegte Taster überspringen
            if pin is None:
                continue

            try:

                button = Button(
                    pin,
                    pull_up=True,
                    bounce_time=0.05,
                    pin_factory=pin_factory
                )

            except Exception as error:

                raise RuntimeError(
                    f"Taster {name} an GPIO "
                    f"{pin} konnte nicht initialisiert "
                    f"werden: {error}"
                ) from error

            # -------------------------------------------------
            # Gedrückt
            # -------------------------------------------------

            button.when_pressed = (
                lambda n=name:
                self._pressed(n)
            )

            # -------------------------------------------------
            # Losgelassen
            # -------------------------------------------------

            button.when_released = (
                lambda n=name:
                self._released(n)
            )

            self.buttons[name] = button

            print(
                f"Taster {name}: "
                f"GPIO {pin}"
            )

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

        self.callback(
            name,
            "pressed"
        )

    # =====================================================
    # TASTER LOSGELASSEN
    # =====================================================

    def _released(
        self,
        name
    ):

        print(
            f"Taster losgelassen: {name}"
        )

        self.callback(
            name,
            "released"
        )
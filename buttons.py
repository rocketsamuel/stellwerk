class Buttons:

    def __init__(self, pins, callback):

        self.buttons = {}

        # Wenn noch keine GPIOs eingetragen sind,
        # brauchen wir gpiozero überhaupt nicht.
        active_pins = {
            name: pin
            for name, pin in pins.items()
            if pin is not None
        }

        if not active_pins:
            print("Keine Taster-GPIOs konfiguriert.")
            return

        try:
            from gpiozero import Button
        except ImportError:
            raise RuntimeError(
                "gpiozero ist für angeschlossene Taster "
                "nicht installiert."
            )

        for name, pin in active_pins.items():

            button = Button(
                pin,
                pull_up=True,
                bounce_time=0.05
            )

            button.when_pressed = (
                lambda name=name:
                callback(name)
            )

            self.buttons[name] = button

    def close(self):

        for button in self.buttons.values():
            button.close()

        self.buttons.clear()

from config import SIGNALS


class SignalController:

    def __init__(self, z21):
        self.z21 = z21
        self.states = {}

    def command(self, signal_name, aspect):
        if signal_name not in SIGNALS:
            raise ValueError(f"Unbekanntes Signal: {signal_name}")

        config = SIGNALS[signal_name]
        aspects = config.get("aspects", {})

        if aspect not in aspects:
            raise ValueError(
                f"Ungültiger Signalbegriff für {signal_name}: {aspect}"
            )

        output = aspects[aspect]
        address = output["address"]
        position = output["position"]

        print(
            f"Signal {signal_name}: {aspect} "
            f"(Adresse {address} -> {position})"
        )

        self.z21.set_turnout(address, position)
        self.states[signal_name] = aspect

    def command_for_route(self, route):
        for signal_name, aspect in route.get("signals", {}).items():
            self.command(signal_name, aspect)

    def test_output(self, address, position):
        configured_addresses = {
            address
            for config in SIGNALS.values()
            for address in config.get("addresses", [])
        }

        if address not in configured_addresses:
            raise ValueError(f"Keine konfigurierte Signaladresse: {address}")

        if position not in ("straight", "turnout"):
            raise ValueError("Stellung muss straight oder turnout sein")

        print(f"Signaltest: Adresse {address} -> {position}")
        self.z21.set_turnout(address, position)

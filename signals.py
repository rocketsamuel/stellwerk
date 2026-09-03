from config import SIGNALS


class SignalController:

    def __init__(self, z21):
        self.z21 = z21
        self.states = {}

        self.addresses = {
            address
            for config in SIGNALS.values()
            for address in config.get("addresses", [])
        }

        self.basic_address_states = {}

        self.extended_addresses = {
            config["raw_address"]: name
            for name, config in SIGNALS.items()
            if config.get("type") == "dcc_ext"
        }

    def uses_address(self, address):
        return address in self.addresses

    def basic_addresses(self):
        return self.addresses

    def update_basic(self, address, position):
        self.basic_address_states[address] = position

        for signal_name, config in SIGNALS.items():
            if address not in config.get("addresses", []):
                continue

            aspects = config.get("aspects", {})

            for aspect, outputs in sorted(
                aspects.items(),
                key=lambda item: len(item[1]),
                reverse=True
            ):
                if all(
                    self.basic_address_states.get(output["address"])
                    == output["position"]
                    for output in outputs
                ):
                    self.states[signal_name] = aspect
                    return (
                        signal_name,
                        config.get("display_name", signal_name),
                        aspect,
                        config.get("indicator_led"),
                    )

        return None, None, None, None

    def extended_raw_addresses(self):
        return self.extended_addresses.keys()

    def update_extended(self, raw_address, value):
        signal_name = self.extended_addresses.get(raw_address)

        if signal_name is None:
            return None, None, None

        config = SIGNALS[signal_name]
        aspect = config.get("dcc_ext_aspects", {}).get(value)
        self.states[signal_name] = aspect or f"DCCext {value}"

        return signal_name, aspect, config.get("indicator_led")

    def command(self, signal_name, aspect):
        if signal_name not in SIGNALS:
            raise ValueError(f"Unbekanntes Signal: {signal_name}")

        config = SIGNALS[signal_name]
        aspects = config.get("aspects", {})

        if aspect not in aspects:
            raise ValueError(
                f"Ungültiger Signalbegriff für {signal_name}: {aspect}"
            )

        outputs = aspects[aspect]

        print(f"Signal {signal_name}: {aspect}")

        for output in outputs:
            address = output["address"]
            position = output["position"]

            print(f"  Adresse {address} -> {position}")
            self.z21.set_turnout(address, position)

        self.states[signal_name] = aspect

    def command_for_route(self, route):
        for signal_name, aspect in route.get("signals", {}).items():
            self.command(signal_name, aspect)

    def test_output(self, address, position):
        if not self.uses_address(address):
            raise ValueError(f"Keine konfigurierte Signaladresse: {address}")

        if position not in ("straight", "turnout"):
            raise ValueError("Stellung muss straight oder turnout sein")

        print(f"Signaltest: Adresse {address} -> {position}")
        self.z21.set_turnout(address, position)

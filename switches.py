from config import SWITCHES


class SwitchController:

    def __init__(
        self,
        z21
    ):

        self.z21 = z21

        # Bekannte Stellung jeder Weiche
        self.states = {}

        # Z21-Adresse -> Weichenname
        self.address_map = {}

        for (
            name,
            config
        ) in SWITCHES.items():

            if config["type"] == "turnout":

                address = config["address"]

                self.address_map[
                    address
                ] = name

    # --------------------------------------------------
    # WEICHE STELLEN
    # --------------------------------------------------

    def command(
        self,
        switch_name,
        position
    ):

        config = SWITCHES.get(
            switch_name
        )

        if config is None:

            raise ValueError(
                f"Unbekannte Weiche: "
                f"{switch_name}"
            )

        if config["type"] != "turnout":

            raise ValueError(
                f"Weiche {switch_name} "
                f"ist kein normales turnout."
            )

        if position not in (
            "straight",
            "turnout"
        ):

            raise ValueError(
                f"Ungültige Stellung: "
                f"{position}"
            )

        print(
            f"Weiche {switch_name} "
            f"auf {position} stellen"
        )

        self.z21.set_turnout(
            config["address"],
            position
        )

    # --------------------------------------------------
    # Z21 RÜCKMELDUNG
    # --------------------------------------------------

    def update(
        self,
        address,
        position
    ):

        switch_name = self.address_map.get(
            address
        )

        if switch_name is None:

            print(
                f"Z21: unbekannte "
                f"Weichenadresse {address}"
            )

            return None

        self.states[
            switch_name
        ] = position

        print(
            f"Weiche {switch_name}: "
            f"{position}"
        )

        return switch_name

    # --------------------------------------------------
    # STELLUNG ABFRAGEN
    # --------------------------------------------------

    def get_position(
        self,
        switch_name
    ):

        return self.states.get(
            switch_name
        )

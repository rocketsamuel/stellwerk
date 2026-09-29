import unittest
from unittest.mock import Mock

from config import ROUTES, SIGNALS
from signals import SignalController
from z21 import Z21


class ShuntingSignalTests(unittest.TestCase):
    def setUp(self):
        self.z21 = Z21.__new__(Z21)
        self.z21.socket = Mock()
        self.leds = Mock()
        self.signals = SignalController(self.z21, self.leds)

    def packets(self):
        return [call.args[0] for call in self.z21.socket.sendto.call_args_list]

    def test_start_route_and_stop_send_correct_packets(self):
        self.signals.initialize_led_signals()
        self.signals.command_for_route(ROUTES["EOW5_HBF4"])
        self.signals.command("ls5", "Hp0")
        self.assertEqual(self.packets(), [
            bytes.fromhex("0a 00 40 00 54 00 80 00 00 d4"),
            bytes.fromhex("0a 00 40 00 54 00 80 41 00 95"),
            bytes.fromhex("0a 00 40 00 54 00 80 00 00 d4"),
        ])
        self.assertEqual(self.signals.states["ls5"], "Hp0")
        self.assertEqual(
            [call.args[1] for call in self.leds.shunting_signal.call_args_list],
            ["Hp0", "Sh1", "Hp0"],
        )

    def test_received_aspects_update_panel_without_sending(self):
        for value, aspect in [(65, "Sh1"), (0, "Hp0"), (99, None)]:
            result = self.signals.update_extended(128, value)
            self.assertEqual(result, ("ls5", aspect, None))
            self.leds.shunting_signal.assert_called_with(
                SIGNALS["ls5"]["aspect_leds"], aspect
            )
        self.assertEqual(self.signals.states["ls5"], "DCCext 99")
        self.z21.socket.sendto.assert_not_called()
        self.assertEqual(self.signals.update_extended(119, 16), ("n4", "Hp1", 21))
        self.assertEqual(self.signals.update_extended(500, 65), (None, None, None))
        self.assertEqual(self.signals.update_extended(125, 65), (None, None, None))

    def test_invalid_commands_do_not_send(self):
        with self.assertRaises(ValueError):
            self.signals.command("ls5", "Hp1")
        for address, value in [(-1, 0), (2048, 0), (128, -1), (128, 256)]:
            with self.assertRaises(ValueError):
                self.z21.set_extended_accessory(address, value)
        self.z21.socket.sendto.assert_not_called()


if __name__ == "__main__":
    unittest.main()

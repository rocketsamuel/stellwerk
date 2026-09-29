import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from z21 import Z21


class NightDimmingTests(unittest.TestCase):
    def test_start_sends_dimming_after_z21_start(self):
        spec = importlib.util.spec_from_file_location(
            "stellwerk_startup_test", Path(__file__).with_name("main.py")
        )
        main = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"leds": Mock(), "buttons": Mock()}):
            spec.loader.exec_module(main)
        app = main.Stellwerk.__new__(main.Stellwerk)
        app.leds = Mock()
        app.signals = Mock()
        app.signals.extended_raw_addresses.return_value = []
        app.signals.basic_addresses.return_value = []
        app.switches = Mock(address_map={})
        app.z21 = Mock()
        app.log_z21_broadcasts = False
        app.update_p4_indicator = Mock()
        app.start()
        app.z21.set_turnout.assert_called_once_with(820, "turnout")
        self.assertEqual(
            [call[0] for call in app.z21.mock_calls],
            ["start", "set_turnout"],
        )
        app.z21.reset_mock()
        with patch.object(main, "NIGHT_DIMMING_ADDRESS", None):
            app.start()
        app.z21.set_turnout.assert_not_called()

    def test_accessory_packet_address_and_checksums(self):
        z21 = Z21.__new__(Z21)
        z21.socket = Mock()
        with patch("z21.time.sleep"):
            z21.set_turnout(820, "turnout")
            z21.set_turnout(820, "straight")
        self.assertEqual(
            [call.args[0] for call in z21.socket.sendto.call_args_list],
            [bytes.fromhex(packet) for packet in [
                "09 00 40 00 53 03 33 89 ea",
                "09 00 40 00 53 03 33 81 e2",
                "09 00 40 00 53 03 33 88 eb",
                "09 00 40 00 53 03 33 80 e3",
            ]],
        )


if __name__ == "__main__":
    unittest.main()

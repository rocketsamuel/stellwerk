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
        app.z21.set_turnout.assert_called_once_with(816, "turnout")
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
            z21.set_turnout(816, "turnout")
            z21.set_turnout(816, "straight")
        self.assertEqual(
            [call.args[0] for call in z21.socket.sendto.call_args_list],
            [bytes.fromhex(packet) for packet in [
                "09 00 40 00 53 03 2f 89 f6",
                "09 00 40 00 53 03 2f 81 fe",
                "09 00 40 00 53 03 2f 88 f7",
                "09 00 40 00 53 03 2f 80 ff",
            ]],
        )


if __name__ == "__main__":
    unittest.main()

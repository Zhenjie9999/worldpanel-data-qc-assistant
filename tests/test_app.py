import unittest

from app import access_urls, parse_args


class AppTests(unittest.TestCase):
    def test_default_mode_stays_local_only(self):
        args = parse_args([])

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8765)
        self.assertFalse(args.no_browser)

    def test_intranet_mode_listens_on_all_interfaces(self):
        args = parse_args(["--intranet", "--no-browser"])

        self.assertEqual(args.host, "0.0.0.0")
        self.assertTrue(args.no_browser)

    def test_access_urls_lists_lan_addresses_for_all_interface_binding(self):
        urls = access_urls("0.0.0.0", 8765, addresses=["172.20.130.157", "127.0.0.1", "10.102.91.159"])

        self.assertEqual(
            urls,
            [
                "http://127.0.0.1:8765",
                "http://172.20.130.157:8765",
                "http://10.102.91.159:8765",
            ],
        )


if __name__ == "__main__":
    unittest.main()

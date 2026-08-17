import os
import tempfile
import unittest
from pathlib import Path

from coolth import config


class TestConfig(unittest.TestCase):

    def setUp(self) -> None:
        # Preserve and clear env that affects config resolution.
        self._saved = {k: os.environ.get(k) for k in (
            "COOLTH_CONFIG", "XDG_CONFIG_HOME")}
        os.environ.pop("COOLTH_CONFIG", None)
        # Point XDG at an empty dir so the user's real config is never read.
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["XDG_CONFIG_HOME"] = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        config.load_config_file()  # reset module state

    def _write(self, text: str) -> str:
        path = Path(self._tmp.name) / "cfg.env"
        path.write_text(text)
        os.environ["COOLTH_CONFIG"] = str(path)
        return str(path)

    def test_basic_keys(self) -> None:
        self._write(
            "account = me@example.com\npassword = secret\nhost = 12345\ncloud = true\n")
        config.load_config_file()
        self.assertEqual(config.get("account"), "me@example.com")
        self.assertEqual(config.get("password"), "secret")
        self.assertEqual(config.get("host"), "12345")
        self.assertEqual(config.get("cloud"), "true")

    def test_comments_blanks_and_quotes(self) -> None:
        self._write(
            "# a comment\n"
            "\n"
            'account = "quoted@example.com"\n'
            "password = 'single'\n"
            "  host = 999  \n"
        )
        config.load_config_file()
        self.assertEqual(config.get("account"), "quoted@example.com")
        self.assertEqual(config.get("password"), "single")
        self.assertEqual(config.get("host"), "999")

    def test_unknown_keys_ignored(self) -> None:
        self._write("account = a\nnot_a_key = x\nPASSWORD = UPPER\n")
        config.load_config_file()
        self.assertEqual(config.get("account"), "a")
        self.assertIsNone(config.get("not_a_key"))
        # Keys are lower-cased, so PASSWORD maps to password.
        self.assertEqual(config.get("password"), "UPPER")

    def test_missing_returns_default(self) -> None:
        self._write("account = a\n")
        config.load_config_file()
        self.assertIsNone(config.get("password"))
        self.assertEqual(config.get("password", "fallback"), "fallback")

    def test_no_file(self) -> None:
        # COOLTH_CONFIG points nowhere and XDG dir is empty.
        os.environ["COOLTH_CONFIG"] = str(
            Path(self._tmp.name) / "does-not-exist.env")
        config.load_config_file()
        self.assertIsNone(config.get("account"))

    def test_as_bool(self) -> None:
        for v in ("1", "true", "TRUE", "yes", "on", "On"):
            self.assertTrue(config.as_bool(v))
        for v in ("0", "false", "no", "off", "", None, "nope"):
            self.assertFalse(config.as_bool(v))


if __name__ == "__main__":
    unittest.main()

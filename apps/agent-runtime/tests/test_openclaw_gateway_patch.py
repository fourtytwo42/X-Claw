import importlib.util
import pathlib
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PATCHER_PATH = REPO_ROOT / "skills" / "xclaw-agent" / "scripts" / "openclaw_gateway_patch.py"
FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures" / "openclaw_patch"


def _load_patcher_module():
    module_name = "xclaw_openclaw_gateway_patch_test"
    spec = importlib.util.spec_from_file_location(module_name, str(PATCHER_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load openclaw_gateway_patch module spec.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class OpenClawGatewayPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patcher = _load_patcher_module()

    def _read_fixture(self, name: str) -> str:
        return (FIXTURES_DIR / name).read_text(encoding="utf-8")

    def test_patch_queued_buttons_v2_accepts_old_anchor(self) -> None:
        raw = self._read_fixture("delivery_send_old_anchor.ts.txt")
        out, changed, err = self.patcher._patch_queued_buttons_v2(raw)
        self.assertIsNone(err)
        self.assertTrue(changed)
        self.assertIn(self.patcher.QUEUED_BUTTONS_MARKER_V4, out)

    def test_patch_queued_buttons_v2_accepts_new_anchor(self) -> None:
        raw = self._read_fixture("delivery_send_new_anchor.ts.txt")
        out, changed, err = self.patcher._patch_queued_buttons_v2(raw)
        self.assertIsNone(err)
        self.assertTrue(changed)
        self.assertIn(self.patcher.QUEUED_BUTTONS_MARKER_V4, out)

    def test_patch_queued_buttons_v2_accepts_regex_variant(self) -> None:
        raw = self._read_fixture("delivery_send_regex_anchor.ts.txt")
        out, changed, err = self.patcher._patch_queued_buttons_v2(raw)
        self.assertIsNone(err)
        self.assertTrue(changed)
        self.assertIn(self.patcher.QUEUED_BUTTONS_MARKER_V4, out)

    def test_patch_queued_buttons_v2_returns_deterministic_error_when_anchor_missing(self) -> None:
        raw = self._read_fixture("delivery_send_no_anchor.ts.txt")
        out, changed, err = self.patcher._patch_queued_buttons_v2(raw)
        self.assertEqual(out, raw)
        self.assertFalse(changed)
        self.assertEqual(err, "queued_buttons_v2_anchor_not_found")

    def test_patch_queued_buttons_v2_is_idempotent(self) -> None:
        raw = self._read_fixture("delivery_send_new_anchor.ts.txt")
        first_out, first_changed, first_err = self.patcher._patch_queued_buttons_v2(raw)
        self.assertIsNone(first_err)
        self.assertTrue(first_changed)
        second_out, second_changed, second_err = self.patcher._patch_queued_buttons_v2(first_out)
        self.assertIsNone(second_err)
        self.assertFalse(second_changed)
        self.assertEqual(second_out.count(self.patcher.QUEUED_BUTTONS_MARKER_V4), 1)

    def test_find_loader_bundles_matches_callback_and_pagination_shape(self) -> None:
        callback_fixture = self._read_fixture("bot_handlers_callback_with_pagination.ts.txt")
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = pathlib.Path(tmp_dir)
            dist = root / "dist"
            dist.mkdir(parents=True, exist_ok=True)
            (dist / "reply-good.js").write_text(callback_fixture, encoding="utf-8")
            (dist / "reply-missing-pagination.js").write_text(
                'bot.on("callback_query", async () => { const x = 1; });',
                encoding="utf-8",
            )
            (dist / "reply-missing-callback.js").write_text(
                'const paginationMatch = data.match(/^commands_page_(\\d+|noop)(?::(.+))?$/);',
                encoding="utf-8",
            )

            bundles = self.patcher._find_loader_bundles(root)
            bundle_names = sorted(path.name for path in bundles)

        self.assertEqual(bundle_names, ["reply-good.js"])

    def test_loader_patch_clears_buttons_immediately_and_does_not_restore_keyboard_on_failure(self) -> None:
        raw = self._read_fixture("bot_handlers_callback_with_pagination.ts.txt")
        out, changed, err = self.patcher._patch_loader_bundle(raw)
        self.assertIsNone(err)
        self.assertTrue(changed)
        self.assertIn(
            'await bot.api.editMessageReplyMarkup(chatId, callbackMessage.message_id, { inline_keyboard: [] });',
            out,
        )
        self.assertIn(self.patcher.DECISION_ACK_MARKER_V29, out)
        self.assertNotIn(
            'await bot.api.editMessageReplyMarkup(chatId, callbackMessage.message_id, { inline_keyboard: kb });',
            out,
        )


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

RUNNER_PATH = pathlib.Path("apps/agent-runtime/scripts/wallet_approval_chain_matrix.py").resolve()
spec = importlib.util.spec_from_file_location("wallet_approval_chain_matrix", RUNNER_PATH)
assert spec and spec.loader
runner_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner_mod
spec.loader.exec_module(runner_mod)


class WalletApprovalChainMatrixTests(unittest.TestCase):
    def _argv(self, tmpdir: str) -> list[str]:
        return [
            "--agent-id",
            "ag_test",
            "--bootstrap-token-file",
            str(pathlib.Path(tmpdir) / "bootstrap.json"),
            "--harvy-address",
            "0x582f6f293e0f49855bb752ae29d6b0565c500d87",
            "--reports-dir",
            tmpdir,
            "--json-report",
            str(pathlib.Path(tmpdir) / "matrix.json"),
        ]

    def _mock_subprocess(self, *, fail_chain: str | None = None):
        chains: list[str] = []

        def _fake_run(cmd: list[str], text: bool, capture_output: bool):
            self.assertTrue(text)
            self.assertTrue(capture_output)
            chain = cmd[cmd.index("--chain") + 1]
            report = pathlib.Path(cmd[cmd.index("--json-report") + 1])
            chains.append(chain)
            ok = fail_chain is None or chain != fail_chain
            report.write_text(json.dumps({"ok": ok, "chain": chain}), encoding="utf-8")
            return mock.Mock(returncode=0 if ok else 1, stdout="", stderr="")

        return chains, _fake_run

    def test_runs_strict_chain_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")
            chains, fake_run = self._mock_subprocess()
            with mock.patch.object(runner_mod.subprocess, "run", side_effect=fake_run):
                rc = runner_mod.main(self._argv(tmpdir))
            self.assertEqual(rc, 0)
            self.assertEqual(chains, ["hardhat_local", "base_sepolia", "ethereum_sepolia", "hedera_testnet"])

            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertTrue(matrix.get("ok"))
            self.assertEqual(
                [s.get("chain") for s in matrix.get("steps", [])],
                ["hardhat_local", "base_sepolia", "ethereum_sepolia", "hedera_testnet"],
            )

    def test_stops_on_first_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")
            chains, fake_run = self._mock_subprocess(fail_chain="hardhat_local")
            with mock.patch.object(runner_mod.subprocess, "run", side_effect=fake_run):
                rc = runner_mod.main(self._argv(tmpdir))
            self.assertEqual(rc, 1)
            self.assertEqual(chains, ["hardhat_local"])

            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertFalse(matrix.get("ok"))
            self.assertEqual(matrix.get("failedAt"), "hardhat_local")
            self.assertEqual(len(matrix.get("steps", [])), 1)

    def test_stops_when_base_sepolia_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")
            chains, fake_run = self._mock_subprocess(fail_chain="base_sepolia")
            with mock.patch.object(runner_mod.subprocess, "run", side_effect=fake_run):
                rc = runner_mod.main(self._argv(tmpdir))
            self.assertEqual(rc, 1)
            self.assertEqual(chains, ["hardhat_local", "base_sepolia"])

            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertFalse(matrix.get("ok"))
            self.assertEqual(matrix.get("failedAt"), "base_sepolia")
            self.assertEqual(len(matrix.get("steps", [])), 2)

    def test_can_resume_from_hedera(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")
            chains, fake_run = self._mock_subprocess()
            argv = self._argv(tmpdir) + ["--start-chain", "hedera_testnet"]
            with mock.patch.object(runner_mod.subprocess, "run", side_effect=fake_run):
                rc = runner_mod.main(argv)
            self.assertEqual(rc, 0)
            self.assertEqual(chains, ["hedera_testnet"])
            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertTrue(matrix.get("ok"))
            self.assertEqual([s.get("chain") for s in matrix.get("steps", [])], ["hedera_testnet"])


if __name__ == "__main__":
    unittest.main()

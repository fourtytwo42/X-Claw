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

        def _fake_run(cmd: list[str], text: bool, capture_output: bool, env: dict[str, str] | None = None):
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
            with mock.patch.object(
                runner_mod,
                "_ensure_solana_localnet_bootstrap",
                return_value=({"XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": "/tmp/faucet.env"}, {"ok": True}),
            ), mock.patch.object(runner_mod.subprocess, "run", side_effect=fake_run):
                rc = runner_mod.main(self._argv(tmpdir))
            self.assertEqual(rc, 0)
            self.assertEqual(chains, ["hardhat_local", "base_sepolia", "ethereum_sepolia", "solana_localnet", "solana_devnet"])

            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertTrue(matrix.get("ok"))
            self.assertEqual(
                [s.get("chain") for s in matrix.get("steps", [])],
                ["hardhat_local", "base_sepolia", "ethereum_sepolia", "solana_localnet", "solana_devnet"],
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

    def test_can_resume_from_ethereum_sepolia(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")
            chains, fake_run = self._mock_subprocess()
            argv = self._argv(tmpdir) + ["--start-chain", "ethereum_sepolia"]
            with mock.patch.object(
                runner_mod,
                "_ensure_solana_localnet_bootstrap",
                return_value=({"XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": "/tmp/faucet.env"}, {"ok": True}),
            ), mock.patch.object(runner_mod.subprocess, "run", side_effect=fake_run):
                rc = runner_mod.main(argv)
            self.assertEqual(rc, 0)
            self.assertEqual(chains, ["ethereum_sepolia", "solana_localnet", "solana_devnet"])
            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertTrue(matrix.get("ok"))
            self.assertEqual([s.get("chain") for s in matrix.get("steps", [])], ["ethereum_sepolia", "solana_localnet", "solana_devnet"])

    def test_can_resume_from_solana_localnet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")
            chains, fake_run = self._mock_subprocess()
            argv = self._argv(tmpdir) + ["--start-chain", "solana_localnet"]
            with mock.patch.object(
                runner_mod,
                "_ensure_solana_localnet_bootstrap",
                return_value=({"XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": "/tmp/faucet.env"}, {"ok": True}),
            ), mock.patch.object(runner_mod.subprocess, "run", side_effect=fake_run):
                rc = runner_mod.main(argv)
            self.assertEqual(rc, 0)
            self.assertEqual(chains, ["solana_localnet", "solana_devnet"])
            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertTrue(matrix.get("ok"))
            self.assertEqual([s.get("chain") for s in matrix.get("steps", [])], ["solana_localnet", "solana_devnet"])

    def test_localnet_provisioning_short_circuits_before_devnet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")
            argv = self._argv(tmpdir) + ["--start-chain", "solana_localnet"]
            with mock.patch.object(runner_mod, "_ensure_solana_localnet_bootstrap", return_value=({}, {"ok": False, "code": "solana_localnet_validator_missing"})):
                rc = runner_mod.main(argv)
            self.assertEqual(rc, 1)
            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertFalse(matrix.get("ok"))
            self.assertEqual(matrix.get("failedAt"), "solana_localnet")
            self.assertEqual([s.get("chain") for s in matrix.get("steps", [])], ["solana_localnet"])
            report = json.loads(pathlib.Path(tmpdir, "xclaw-slice243-solana-localnet-full.json").read_text(encoding="utf-8"))
            self.assertFalse(report.get("ok"))
            self.assertEqual(report.get("preflight", {}).get("solanaLocalnetProvisioning", {}).get("code"), "solana_localnet_validator_missing")

    def test_localnet_env_file_is_passed_to_harness_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bootstrap = pathlib.Path(tmpdir, "bootstrap.json")
            bootstrap.write_text(json.dumps({"token": "t"}), encoding="utf-8")
            env_file = pathlib.Path(tmpdir, "solana-localnet-faucet.env")
            env_file.write_text(
                "\n".join(
                    [
                        "XCLAW_SOLANA_FAUCET_SIGNER_SECRET_SOLANA_LOCALNET=abc",
                        "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET=So11111111111111111111111111111111111111112",
                        "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    ]
                ),
                encoding="utf-8",
            )
            with mock.patch.object(runner_mod, "SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE", env_file), mock.patch.object(
                runner_mod,
                "_ensure_solana_localnet_bootstrap",
                return_value=(
                    {
                        "XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": str(env_file),
                        "XCLAW_SOLANA_FAUCET_SIGNER_SECRET_SOLANA_LOCALNET": "abc",
                    },
                    {"ok": True},
                ),
            ):
                seen_env: dict[str, str] = {}

                def _fake_run(cmd: list[str], text: bool, capture_output: bool, env: dict[str, str] | None = None):
                    chain = cmd[cmd.index("--chain") + 1]
                    report = pathlib.Path(cmd[cmd.index("--json-report") + 1])
                    if chain == "solana_localnet" and env:
                        seen_env.update(env)
                    report.write_text(json.dumps({"ok": True, "chain": chain}), encoding="utf-8")
                    return mock.Mock(returncode=0, stdout="", stderr="")

                with mock.patch.object(runner_mod.subprocess, "run", side_effect=_fake_run):
                    rc = runner_mod.main(self._argv(tmpdir) + ["--start-chain", "solana_localnet"])
            self.assertEqual(rc, 0)
            self.assertEqual(seen_env.get("XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE"), str(env_file))
            self.assertEqual(seen_env.get("XCLAW_SOLANA_FAUCET_SIGNER_SECRET_SOLANA_LOCALNET"), "abc")

    def test_localnet_provisioning_records_resolved_mints(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")
            with mock.patch.object(
                runner_mod,
                "_ensure_solana_localnet_bootstrap",
                return_value=(
                    {
                        "XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": "/tmp/faucet.env",
                        "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET": "BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6",
                        "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET": "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3",
                    },
                    {
                        "ok": True,
                        "bootstrapEnvFile": "/tmp/faucet.env",
                        "resolvedWrappedMint": "BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6",
                        "resolvedStableMint": "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3",
                    },
                ),
            ):
                def _fake_run(cmd: list[str], text: bool, capture_output: bool, env: dict[str, str] | None = None):
                    chain = cmd[cmd.index("--chain") + 1]
                    report = pathlib.Path(cmd[cmd.index("--json-report") + 1])
                    report.write_text(json.dumps({"ok": True, "chain": chain}), encoding="utf-8")
                    return mock.Mock(returncode=0, stdout="", stderr="")

                with mock.patch.object(runner_mod.subprocess, "run", side_effect=_fake_run):
                    rc = runner_mod.main(self._argv(tmpdir) + ["--start-chain", "solana_localnet"])
            self.assertEqual(rc, 0)
            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            local_step = matrix.get("steps", [])[0]
            self.assertEqual(local_step.get("chain"), "solana_localnet")
            provision = local_step.get("report", {}).get("preflight", {}).get("solanaLocalnetProvisioning", {})
            self.assertEqual(provision.get("bootstrapEnvFile"), "/tmp/faucet.env")
            self.assertEqual(provision.get("resolvedWrappedMint"), "BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6")
            self.assertEqual(provision.get("resolvedStableMint"), "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3")

    def test_solana_devnet_remains_final_chain(self) -> None:
        self.assertEqual(runner_mod.CHAIN_ORDER[-1], "solana_devnet")

    def test_matrix_preserves_machine_readable_devnet_unsupported_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pathlib.Path(tmpdir, "bootstrap.json").write_text(json.dumps({"token": "t"}), encoding="utf-8")

            def _fake_run(cmd: list[str], text: bool, capture_output: bool, env: dict[str, str] | None = None):
                chain = cmd[cmd.index("--chain") + 1]
                report = pathlib.Path(cmd[cmd.index("--json-report") + 1])
                payload = {"ok": True, "chain": chain}
                rc = 0
                if chain == "solana_devnet":
                    payload = {
                        "ok": False,
                        "chain": chain,
                        "results": [
                            {
                                "name": "solana_devnet_trade_evidence_boundary",
                                "ok": False,
                                "message": "scenario failed",
                                "details": {
                                    "class": "unsupported_live_evidence",
                                    "error": "No Jupiter-quotable Solana devnet trade pair is available for truthful live evidence.",
                                },
                            }
                        ],
                        "preflight": {
                            "solanaDevnetTradePair": {
                                "quoteable": False,
                                "reason": "solana_devnet_trade_pair_unavailable",
                            }
                        },
                    }
                    rc = 1
                report.write_text(json.dumps(payload), encoding="utf-8")
                return mock.Mock(returncode=rc, stdout="", stderr="")

            with mock.patch.object(
                runner_mod,
                "_ensure_solana_localnet_bootstrap",
                return_value=({"XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": "/tmp/faucet.env"}, {"ok": True}),
            ), mock.patch.object(runner_mod.subprocess, "run", side_effect=_fake_run):
                rc = runner_mod.main(self._argv(tmpdir))
            self.assertEqual(rc, 1)
            matrix = json.loads(pathlib.Path(tmpdir, "matrix.json").read_text(encoding="utf-8"))
            self.assertEqual(matrix.get("failedAt"), "solana_devnet")
            last = matrix.get("steps", [])[-1]
            self.assertEqual(last.get("chain"), "solana_devnet")
            self.assertEqual(
                last.get("report", {}).get("preflight", {}).get("solanaDevnetTradePair", {}).get("reason"),
                "solana_devnet_trade_pair_unavailable",
            )


if __name__ == "__main__":
    unittest.main()

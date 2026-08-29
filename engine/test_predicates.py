#!/usr/bin/env python3
"""Tests for the predicates and the dispatcher.

Run:  python3 engine/test_predicates.py

Stdlib only, like everything else here -- a clone must be able to verify the
engine without installing anything.

These are not evidence of a false-positive rate. Every case below was written
by whoever wrote the predicate, which is exactly the circularity that made the
hollow-test rule look safe at 0/4 right up until it rejected three legitimate
conditional skips. What they do prove is that the rules mean what the policy
says they mean -- that `skipif` survives, that a hedge in the same sentence
suppresses, that the shell splitter sees past `&&`. The real false-positive
rate comes from shadow mode on real work, and nothing is promoted out of
`mode: "log"` without it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import ledger  # noqa: E402
import predicates  # noqa: E402

with open(os.path.join(ROOT, "policy", "checks.json"), encoding="utf-8") as fh:
    POLICY = json.load(fh)
with open(os.path.join(ROOT, "policy", "domains.json"), encoding="utf-8") as fh:
    DOMAINS = json.load(fh)["domains"]

PARAMS = {c["id"]: c.get("params") or {} for c in POLICY["checks"]}
BASH = PARAMS["prudence.unrecoverable-bash"]
CLAIM = PARAMS["truth-and-integrity.unverified-completion-claim"]
TEST = PARAMS["truth-and-integrity.disabled-or-vacuous-test"]
DOMAIN = PARAMS["prudence.security-domain-touch"]


def bash(command):
    return predicates.unrecoverable_bash(
        {"tool_input": {"command": command}}, BASH, {})


class UnrecoverableBash(unittest.TestCase):
    def test_recursive_force_delete_fires(self):
        self.assertIsNotNone(bash("rm -rf /srv/data"))

    def test_flag_order_does_not_matter(self):
        self.assertIsNotNone(bash("rm -fr /srv/data"))

    def test_fires_past_a_shell_operator(self):
        # The patterns are ^-anchored. Matching the whole string instead of
        # each segment would let every chained command through -- the single
        # most likely way to ship a check that silently never fires.
        self.assertIsNotNone(bash("echo starting && rm -rf /srv/data"))

    def test_fires_under_sudo(self):
        # settings.json rewrites sudo to `sudo -A` on this machine, so a
        # privileged command is the normal shape here, not an edge case.
        self.assertIsNotNone(bash("sudo -A rm -rf /srv/data"))

    def test_talking_about_it_is_not_doing_it(self):
        self.assertIsNone(bash("echo 'rm -rf /srv' >> notes.md"))
        self.assertIsNone(bash("grep -r 'DROP TABLE' migrations/"))

    def test_disposable_paths_are_not_a_loss(self):
        self.assertIsNone(bash("rm -rf node_modules dist"))

    def test_one_real_target_among_disposable_ones_still_fires(self):
        self.assertIsNotNone(bash("rm -rf node_modules /srv/data"))

    def test_force_push_fires_but_lease_does_not(self):
        self.assertIsNotNone(bash("git push --force origin main"))
        self.assertIsNone(bash("git push --force-with-lease origin main"))

    def test_dry_run_is_exempt(self):
        self.assertIsNone(bash("git clean -fd --dry-run"))

    def test_destructive_ddl_is_case_insensitive(self):
        self.assertIsNotNone(bash("psql -c 'drop table users'"))

    def test_recoverable_git_is_deliberately_absent(self):
        # Both are reflog-recoverable and both fire constantly in honest work.
        self.assertIsNone(bash("git reset --hard HEAD~1"))
        self.assertIsNone(bash("git stash drop"))


class CompletionClaim(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp()
        open(os.path.join(self.cwd, "pyproject.toml"), "w").close()

    def tearDown(self):
        shutil.rmtree(self.cwd, ignore_errors=True)

    def run_it(self, message, evidence=(), cwd=None):
        return predicates.completion_claim_without_evidence(
            {"last_assistant_message": message}, CLAIM,
            {"cwd": self.cwd if cwd is None else cwd,
             "evidence": list(evidence)})

    def test_bare_claim_with_no_test_run_fires(self):
        self.assertIsNotNone(self.run_it("All tests pass."))

    def test_a_real_test_run_clears_it(self):
        self.assertIsNone(self.run_it("All tests pass.",
                                      ["python3 -m pytest -q"]))

    def test_an_unrelated_command_does_not_clear_it(self):
        self.assertIsNotNone(self.run_it("All tests pass.", ["git status"]))

    def test_hedged_claims_do_not_fire(self):
        # Both were measured false positives of the claim regex alone.
        self.assertIsNone(self.run_it(
            "This should make the tests pass once you run them."))
        self.assertIsNone(self.run_it(
            "The tests pass locally per their report."))
        self.assertIsNone(self.run_it(
            "I have not run them, but no errors are expected."))

    def test_a_hedge_elsewhere_does_not_excuse_a_bare_claim(self):
        # Hedge scope is the sentence. Message scope would let one honest
        # caveat anywhere excuse a flat assertion everywhere else.
        self.assertIsNotNone(self.run_it(
            "I should refactor this later. All tests pass."))

    def test_disarms_without_test_infrastructure(self):
        empty = tempfile.mkdtemp()
        try:
            self.assertIsNone(self.run_it("All tests pass.", cwd=empty))
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_silence_is_not_a_claim(self):
        self.assertIsNone(self.run_it(""))
        self.assertIsNone(self.run_it("Done -- have a look."))


class DisabledOrVacuousTest(unittest.TestCase):
    def run_it(self, added, path="tests/test_auth.py", key="new_string"):
        return predicates.disabled_or_vacuous_test(
            {"tool_input": {"file_path": path, key: added}}, TEST, {})

    def test_bare_skip_fires(self):
        self.assertIsNotNone(self.run_it(
            "@pytest.mark.skip\ndef test_login():\n    assert thing()\n"))

    def test_skip_with_a_reason_does_not(self):
        self.assertIsNone(self.run_it(
            '@pytest.mark.skip(reason="upstream #4412")\n'
            "def test_login():\n    assert thing()\n"))

    def test_skipif_survives(self):
        # `skip` matches the `skipif` prefix. This is the exact case that
        # broke the predicate before the negative lookahead went in, and it
        # broke it on correct code.
        for line in ('@pytest.mark.skipif(sys.platform == "win32")',
                     "@pytest.mark.skipif(not HAS_GPU)"):
            self.assertIsNone(self.run_it(line + "\ndef test_x():\n    ok()\n"))

    def test_strict_xfail_survives(self):
        self.assertIsNone(self.run_it(
            '@pytest.mark.xfail(strict=True, reason="upstream #4412")\n'
            "def test_x():\n    ok()\n"))

    def test_tautology_fires(self):
        self.assertIsNotNone(self.run_it(
            "def test_login():\n    assert True\n"))

    def test_non_test_files_are_out_of_scope(self):
        self.assertIsNone(self.run_it(
            "def helper():\n    assert True\n", path="src/util.py"))

    def test_deleting_a_tautology_does_not_fire(self):
        # old_string is never read. The check that celebrates removing an
        # `assert True` must not be the one that blocks removing it.
        self.assertIsNone(predicates.disabled_or_vacuous_test(
            {"tool_input": {"file_path": "tests/test_auth.py",
                            "old_string": "    assert True\n",
                            "new_string": "    assert login() is True\n"}},
            TEST, {}))

    def test_a_written_file_is_read_from_content(self):
        self.assertIsNotNone(self.run_it(
            "def test_login():\n    assert True\n", key="content"))


class FirstTouchOfDomain(unittest.TestCase):
    def run_it(self, path, seen=()):
        return predicates.first_touch_of_domain(
            {"tool_input": {"file_path": path}}, DOMAIN,
            {"domains": DOMAINS, "seen_domains": set(seen), "root": None})

    def test_fires_on_a_matching_path(self):
        self.assertIsNotNone(self.run_it("src/auth/session.py"))
        self.assertIsNotNone(self.run_it("app/login_token.ts"))

    def test_once_per_session(self):
        self.assertIsNone(self.run_it("src/auth/session.py",
                                      seen=["security-hardening"]))

    def test_ignores_unrelated_paths(self):
        self.assertIsNone(self.run_it("src/ui/Button.tsx"))

    def test_does_not_reach_for_files_holding_live_secrets(self):
        # Every reaction this can make is written to a plain log.
        self.assertIsNone(self.run_it(".env"))
        self.assertIsNone(self.run_it("k8s/api-secret.yaml"))

    def test_a_missing_domain_is_reported_not_swallowed(self):
        hit = predicates.first_touch_of_domain(
            {"tool_input": {"file_path": "src/auth/session.py"}},
            {"domain": "no-such-domain"},
            {"domains": DOMAINS, "seen_domains": set(), "root": None})
        self.assertIsNotNone(hit)
        self.assertTrue(hit.get("misconfigured"))


class Dispatch(unittest.TestCase):
    """End to end, through the real entry point."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = dict(os.environ)
        self.env["HOME"] = self.tmp
        self.env.pop("BRAIN_ENGINE_OFF", None)
        self.sid = "test-%d" % os.getpid()
        # An armed cwd, not the repo root. The vault has no pyproject.toml and
        # no tests/ directory, so the integrity check disarms there -- which
        # made the "evidence clears the claim" case pass for the wrong reason
        # until its sibling failed and showed why.
        self.armed = tempfile.mkdtemp()
        open(os.path.join(self.armed, "pyproject.toml"), "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.armed, ignore_errors=True)
        try:
            os.remove(ledger.path_for(self.sid))
        except OSError:
            pass

    def call(self, event, payload, env_extra=None):
        env = dict(self.env)
        if env_extra:
            env.update(env_extra)
        payload.setdefault("session_id", self.sid)
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "dispatch.py"), event],
            input=json.dumps(payload), capture_output=True, text=True, env=env)

    def rows(self):
        return ledger.read_rows(self.sid)

    def test_shadow_mode_emits_nothing(self):
        # One stray byte on stdout breaks hook JSON parsing for every other
        # hook on the event, including the sudo rewrite settings.json needs.
        p = self.call("PreToolUse", {"tool_name": "Bash",
                                     "tool_input": {"command": "rm -rf /srv"}})
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "")

    def test_a_fire_reaches_the_ledger_as_would_have(self):
        self.call("PreToolUse", {"tool_name": "Bash", "prompt_id": "t1",
                                 "tool_input": {"command": "rm -rf /srv"}})
        verdicts = [v for r in self.rows() for v in r.get("verdicts") or []]
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0]["id"], "prudence.unrecoverable-bash")
        self.assertEqual(verdicts[0]["would_have"], "log")

    def test_kill_switch_stops_everything(self):
        p = self.call("PreToolUse",
                      {"tool_name": "Bash",
                       "tool_input": {"command": "rm -rf /srv"}},
                      env_extra={"BRAIN_ENGINE_OFF": "1"})
        self.assertEqual(p.stdout, "")
        self.assertEqual(self.rows(), [])

    def test_stop_hook_active_returns_before_any_check(self):
        p = self.call("Stop", {"stop_hook_active": True, "prompt_id": "t1",
                               "last_assistant_message": "All tests pass."})
        self.assertEqual(p.stdout, "")
        self.assertEqual(self.rows(), [])

    def test_evidence_from_the_same_turn_clears_the_stop_check(self):
        self.call("PostToolUse", {"tool_name": "Bash", "prompt_id": "t9",
                                  "tool_input": {"command": "pytest -q"}})
        self.call("Stop", {"prompt_id": "t9", "cwd": self.armed,
                           "last_assistant_message": "All tests pass."})
        verdicts = [v for r in self.rows() for v in r.get("verdicts") or []]
        self.assertEqual(verdicts, [])

    def test_evidence_from_another_turn_does_not_carry_over(self):
        self.call("PostToolUse", {"tool_name": "Bash", "prompt_id": "t9",
                                  "tool_input": {"command": "pytest -q"}})
        self.call("Stop", {"prompt_id": "t10", "cwd": self.armed,
                           "last_assistant_message": "All tests pass."})
        ids = [v["id"] for r in self.rows() for v in r.get("verdicts") or []]
        self.assertIn("truth-and-integrity.unverified-completion-claim", ids)

    def test_the_message_text_is_never_written_down(self):
        secret = "All tests pass. The passphrase is opensesame."
        self.call("Stop", {"prompt_id": "t11", "cwd": self.armed,
                           "last_assistant_message": secret})
        with open(ledger.path_for(self.sid), encoding="utf-8") as fh:
            raw = fh.read()
        self.assertNotIn("opensesame", raw)
        self.assertIn("last_assistant_message_len", raw)

    def test_garbage_on_stdin_fails_open(self):
        env = dict(self.env)
        p = subprocess.run(
            [sys.executable, os.path.join(HERE, "dispatch.py"), "PreToolUse"],
            input="not json at all", capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "")

    def test_dispatch_stays_inside_its_budget(self):
        self.call("PreToolUse", {"tool_name": "Bash", "prompt_id": "t12",
                                 "tool_input": {"command": "ls -la"}})
        budget = POLICY["budgets"]["dispatch_ms"]
        for row in self.rows():
            if "dispatch_ms" in row:
                self.assertLess(row["dispatch_ms"], budget,
                                "dispatch exceeded budgets.dispatch_ms")


if __name__ == "__main__":
    unittest.main(verbosity=2)

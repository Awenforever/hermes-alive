"""Synthetic durable-state probe for disposable real-install admission only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("create", "check"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    args = parser.parse_args()
    profile = args.profile.resolve(strict=True)
    assert profile == Path(os.environ["HERMES_HOME"]).resolve(strict=True)
    hooks = profile / "skills" / "hermes-alive" / "hooks"
    assert hooks.is_dir(), "installed runtime source is required"
    sys.path.insert(0, str(hooks))
    from alive_kernel import EventEnvelope, ExperienceJournal, Sensitivity
    from alive_kernel.content_vault import ContentVault
    from alive_kernel.privacy import LocalIdentityProtector

    kernel = profile / "plugin-data" / "hermes-alive" / "runtime" / "kernel"
    journal_path = kernel / "experience.sqlite3"
    if args.mode == "check":
        # Do not silently create replacement state when preservation failed.
        for path in (journal_path, kernel / "identity.key",
                     kernel / "content-vault" / "content.key",
                     kernel / "content-vault" / "content.sqlite3"):
            assert path.is_file(), "durable fixture state was lost"
    journal = ExperienceJournal(journal_path)
    vault = ContentVault(kernel / "content-vault", backup_root=kernel / "content-backups")
    payload = {"note": "synthetic durable private installation fixture"}
    if args.mode == "create":
        assert not args.expected.exists(), "do not replace the baseline"
        protector = LocalIdentityProtector(kernel / "identity.key")
        subject = protector.pseudonym("admission", "synthetic-owner")
        reference = vault.put_json(payload, subject=subject, purpose="admission.fixture",
                                   sensitivity=Sensitivity.PRIVATE, content_id="admission:content")
        record = journal.append(EventEnvelope(
            event_id="admission:event", event_type="admission.observed",
            source="test.fixture", actor="user:fixture", subject=subject,
            sensitivity=Sensitivity.PRIVATE, payload={"content": reference.to_event_payload()},
        ))
        journal.advance_checkpoint("admission-fixture", record.sequence)
        expected = {"event": record.event.canonical_json(), "sequence": record.sequence,
                    "subject": subject, "content_id": reference.content_id,
                    "keys": {str(path.relative_to(kernel)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in (kernel / "identity.key", vault.key_path)}}
        args.expected.write_text(json.dumps(expected), encoding="utf-8")
    else:
        expected = json.loads(args.expected.read_text(encoding="utf-8"))
        record = journal.get("admission:event")
        assert record is not None and record.sequence == expected["sequence"]
        assert record.event.canonical_json() == expected["event"]
        assert journal.checkpoint("admission-fixture") == expected["sequence"]
        for relative, digest in expected["keys"].items():
            assert hashlib.sha256((kernel / relative).read_bytes()).hexdigest() == digest
        assert vault.resolve_json(expected["content_id"], expected_subject=expected["subject"],
                                  expected_purpose="admission.fixture") == payload
    print("HERMES_ALIVE_ADMISSION_DURABLE_STATE_OK=" + args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

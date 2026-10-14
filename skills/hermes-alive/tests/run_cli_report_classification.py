#!/usr/bin/env python3
"""Transport reports never imply delivery, completion or human benefit."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.transport_receipts import CliReportKind as Kind, classify_cli_report
from alive_kernel.transport_receipts import reported_message_reference
from alive_kernel.privacy import LocalIdentityProtector


def main():
    cases = [
        ({"success": True}, 0, Kind.SUCCESS_REPORTED),
        ({"success": True, "external_delivery_proven": True,
          "delivery_succeeded": True}, 0, Kind.SUCCESS_REPORTED),
        ({"success": True}, 1, Kind.UNKNOWN),
        ({"success": "yes"}, 0, Kind.UNKNOWN),
        ({"success": True}, True, Kind.UNKNOWN),
        ({"success": True}, None, Kind.UNKNOWN),
        ({"success": True, "skipped": True}, 0, Kind.SKIP_REPORTED),
        ({"skipped": True, "partial_success": True}, 0, Kind.UNKNOWN),
        ({"skipped": True, "error": "private error"}, 0, Kind.UNKNOWN),
        ({"partial_success": True, "error": "private error"}, 1, Kind.PARTIAL_REPORTED),
        ({"success": True, "error": "private error"}, 0, Kind.ERROR_REPORTED),
        ({"error": {"private": "content"}}, 1, Kind.UNKNOWN),
        ({"success": False}, 1, Kind.UNKNOWN),
        ([], 0, Kind.UNKNOWN),
    ]
    for payload, code, kind in cases:
        report = classify_cli_report(json.dumps(payload), code)
        assert report.kind is kind, (payload, code, report)
        assert report.to_document()["external_delivery_proven"] is False
        assert "private" not in json.dumps(report.to_document())
    for text in ('{"success": true, "success": false}', '{"success": NaN}',
                 'not JSON', '{"data": {"x": 1, "x": 2}}'):
        assert classify_cli_report(text, 0).kind is Kind.UNKNOWN
    crash = classify_cli_report('{}', 0xC0000005)
    assert crash.kind is Kind.UNKNOWN and crash.exit_code == 0xC0000005
    route = {'platform': 'synthetic', 'profile': 'test', 'chat_id': 'chat', 'thread_id': None}
    with tempfile.TemporaryDirectory() as directory:
        protector = LocalIdentityProtector(Path(directory) / 'identity.key')
        report = classify_cli_report('{"success":true,"message_id":"private-message-id"}', 0)
        assert report.reported_message_id == 'private-message-id'
        assert 'private-message-id' not in repr(report) + json.dumps(report.to_document())
        ref = reported_message_reference(protector, route, report.reported_message_id)
        assert len(ref) == 64 and 'private-message-id' not in ref
        for key in route:
            assert reported_message_reference(protector, {**route, key:'another'}, report.reported_message_id) != ref
        for invalid in ('', ' id', 'id\n', 123, 'x'*513, '\ud800'):
            assert classify_cli_report(json.dumps({'success':True,'message_id':invalid}), 0).reported_message_id is None
            assert reported_message_reference(protector, route, invalid) is None
        assert classify_cli_report('{"success":true,"skipped":true,"message_id":"id"}', 0).reported_message_id is None
    for text in ("x" * 65537, "界" * 22000, "invalid\ud800"):
        try:
            classify_cli_report(text, 0)
        except ValueError:
            pass
        else:
            raise AssertionError("unbounded report accepted")
    print("HERMES_ALIVE_CLI_REPORT_CLASSIFICATION_OK")


if __name__ == "__main__":
    main()

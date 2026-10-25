#!/usr/bin/env python3
"""Text compiler isolation; stub callbacks here are not runtime qualification."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.cli_send_contract import CliSendContractError, compile_text_cli_plan


def main():
    with tempfile.TemporaryDirectory(prefix="alive-cli-contract-") as directory:
        home = Path(directory).resolve()
        route = {"platform": "test", "profile": "fixture", "chat_id": "chat", "thread_id": None}
        body = "私人内容\n\n[研究](https://example.invalid/paper)"
        def document(text=body, fmt="markdown"):
            return {"schema_version": 1, "capability": "hermes.channel.send",
                    "operation": {"text": text, "format": fmt}}
        def compile(doc=None, binding=None, **overrides):
            options = dict(profile_id="fixture", hermes_home=home,
                           resolve_target=lambda platform, reference: (reference, None, None),
                           extract_media=lambda text: ([], text), observe_profile_home=lambda: home)
            options.update(overrides)
            return compile_text_cli_plan(doc or document(), binding or route, **options)
        plan = compile()
        assert plan.stdin_text == body and body not in repr(plan)
        assert body not in plan.arguments and plan.arguments[-3:] == ("--file", "-", "--json")
        assert plan.target == "test:chat" and str(home) not in repr(plan)
        failures = [
            lambda: compile(profile_id="other"),
            lambda: compile(hermes_home=Path("relative")),
            lambda: compile(observe_profile_home=lambda: home.parent),
            lambda: compile(binding={**route, "chat_id": ""}),
            lambda: compile(binding={**route, "chat_id": "chat\nother"}),
            lambda: compile(binding={**route, "unexpected": "value"}),
            lambda: compile(resolve_target=lambda p, r: ("other", None, None)),
            lambda: compile(resolve_target=lambda p, r: ("chat", "thread", None)),
            lambda: compile(extract_media=lambda text: ([], "changed text")),
            lambda: compile(extract_media=lambda text: ([('synthetic.pdf', False)], text)),
            lambda: compile(document(fmt="plain")),
        ]
        for text in ("MEDIA:/nonexistent.pdf", "`MEDIA:/quoted.pdf`", "media:/later-created",
                     "[[audio_as_voice]]hello", "[[as_document]]hello", "hello\0there"):
            failures.append(lambda text=text: compile(document(text)))
        for operation in failures:
            try:
                operation()
            except CliSendContractError:
                pass
            else:
                raise AssertionError("CLI contract boundary was crossed")
        threaded = compile(binding={**route, "thread_id": "topic"},
                           resolve_target=lambda p, r: ("chat", "topic", None))
        assert threaded.target == "test:chat:topic"
    print("HERMES_ALIVE_CLI_SEND_CONTRACT_OK")


if __name__ == "__main__":
    main()

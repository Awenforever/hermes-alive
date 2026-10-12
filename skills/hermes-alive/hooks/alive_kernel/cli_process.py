"""Operator-owned process launcher; not automatic Hermes runtime discovery.

File pins qualify only named artifacts, not an entire interpreter/import graph.
No installed production transport is selected or enabled by this module.
"""
from dataclasses import dataclass, field
import hashlib
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Mapping

from .cli_send_contract import CliSendPlan


class CliProcessUncertain(RuntimeError):
    """No zero-effect or terminal delivery conclusion may follow this error."""


@dataclass(frozen=True, slots=True)
class OperatorCliProcess:
    prefix: tuple[str, ...] = field(repr=False)
    cwd: Path = field(repr=False)
    profile_id: str = field(repr=False)
    hermes_home: Path = field(repr=False)
    environment: Mapping[str, str] = field(repr=False)
    artifact_pins: Mapping[Path, str] = field(repr=False)
    timeout_seconds: float = 30.0
    output_limit_bytes: int = 65536

    def __post_init__(self):
        # Own immutable snapshots: caller mutation cannot silently replace pins,
        # command or environment after admission.
        from types import MappingProxyType
        object.__setattr__(self, "prefix", tuple(self.prefix))
        object.__setattr__(self, "environment", MappingProxyType(dict(self.environment)))
        object.__setattr__(self, "artifact_pins", MappingProxyType(dict(self.artifact_pins)))
        if (not self.prefix or not all(isinstance(v, str) and "\0" not in v for v in self.prefix)
                or not Path(self.prefix[0]).is_absolute()
                or not self.cwd.is_absolute() or not self.cwd.is_dir()
                or not self.hermes_home.is_absolute() or not self.hermes_home.is_dir()
                or self.environment.get("HERMES_HOME") != str(self.hermes_home.resolve())
                or isinstance(self.timeout_seconds, bool)
                or not isinstance(self.timeout_seconds, (int, float))
                or not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 300
                or type(self.output_limit_bytes) is not int
                or not 1 <= self.output_limit_bytes <= 65536):
            raise ValueError("operator process binding is invalid")
        if Path(self.prefix[0]) not in self.artifact_pins:
            raise ValueError("operator executable must have an artifact pin")
        folded_keys = [key.upper() for key in self.environment if isinstance(key, str)]
        if len(set(folded_keys)) != len(self.environment):
            raise ValueError("operator environment has ambiguous case variants")
        for path, digest in self.artifact_pins.items():
            if (not isinstance(path, Path) or not path.is_absolute()
                    or not isinstance(digest, str) or len(digest) != 64
                    or any(char not in "0123456789abcdef" for char in digest)):
                raise ValueError("operator artifact pin is invalid")
        for key, value in self.environment.items():
            if (not isinstance(key, str) or not key or "=" in key or "\0" in key
                    or not isinstance(value, str) or "\0" in value):
                raise ValueError("operator environment is invalid")

    def _validate(self, plan: CliSendPlan):
        if plan.profile_id != self.profile_id or plan.hermes_home.resolve() != self.hermes_home.resolve():
            raise ValueError("compiled plan belongs to another operator profile")
        # The plan itself is not a permit, but direct callers may not inject
        # arbitrary CLI flags or substitute a body in the command arguments.
        if plan.arguments != ("send", "--to", plan.target, "--file", "-", "--json"):
            raise ValueError("compiled command arguments changed")
        for path, expected in self.artifact_pins.items():
            with path.open("rb") as artifact:
                if not path.is_file() or hashlib.file_digest(artifact, "sha256").hexdigest() != expected:
                    raise ValueError("operator runtime artifact changed")

    def __call__(self, plan: CliSendPlan) -> tuple[str, int]:
        self._validate(plan)
        body = plan.stdin_text.encode("utf-8")
        if len(body) > 1048576:
            raise ValueError("process input exceeds the qualified capture budget")
        # Regular temporary files avoid pipe deadlocks, inherited-pipe EOF waits
        # and raw body exposure in argv. They can hold sensitive transient bytes;
        # they are not encrypted persistent memory or secure-erasure guarantees.
        with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            source.write(body)
            source.seek(0)
            process = None
            try:
                process = subprocess.Popen(
                    [*self.prefix, *plan.arguments], cwd=self.cwd, env=dict(self.environment),
                    stdin=source, stdout=output, stderr=errors, shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                deadline = time.monotonic() + self.timeout_seconds
                while process.poll() is None:
                    if (time.monotonic() >= deadline
                            or os.fstat(output.fileno()).st_size > self.output_limit_bytes
                            or os.fstat(errors.fileno()).st_size > self.output_limit_bytes):
                        raise CliProcessUncertain("process exceeded time or output observation budget")
                    time.sleep(0.02)
                if (os.fstat(output.fileno()).st_size > self.output_limit_bytes
                        or os.fstat(errors.fileno()).st_size > self.output_limit_bytes):
                    raise CliProcessUncertain("process exceeded output observation budget")
                output.seek(0)
                try:
                    stdout = output.read(self.output_limit_bytes + 1).decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    raise CliProcessUncertain("process stdout is not lossless UTF-8") from None
                return stdout, process.returncode
            except OSError:
                raise CliProcessUncertain("process launch or capture could not be established") from None
            finally:
                if process is not None and process.poll() is None:
                    # Own child only. Killing it is not evidence that descendants
                    # stopped or that external effects did not already happen.
                    process.kill()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        raise CliProcessUncertain("owned process termination remains uncertain") from None

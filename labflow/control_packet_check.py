"""Read-only command boundary for one explicitly pinned local control packet."""

from __future__ import annotations

import argparse
import json
import sys

from .control_packet_audit import audit_control_packet, ControlPacketAuditError


_AUDIT_CODES = frozenset({
    "packet_invalid_argument", "packet_unavailable", "packet_index_invalid",
    "packet_index_mismatch", "packet_index_changed", "packet_path_invalid",
    "packet_limit_exceeded", "packet_payload_mismatch", "packet_json_invalid",
    "packet_zip_invalid",
})


class _InvalidArguments(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse messages can contain caller-controlled option values.
        raise _InvalidArguments() from None


def _parser():
    parser = _Parser(
        prog="python -B -m labflow.control_packet_check", add_help=False,
        allow_abbrev=False, exit_on_error=False,
        description="Read-only audit of one explicitly pinned local control-source packet.",
    )
    parser.add_argument("--packet-dir", required=True, action="append", metavar="LOCAL_DIR",
                        help="Local packet directory, supplied exactly once.")
    parser.add_argument("--index-sha256", required=True, action="append", metavar="LOWERCASE_SHA256",
                        help="Index SHA-256 from a separate trusted receipt, supplied exactly once.")
    parser.add_argument("--help", action="store_true", help="Show this help; valid only by itself.")
    return parser


def _arguments(parser, argv):
    if not all(isinstance(value, str) for value in argv):
        raise _InvalidArguments()
    if "--help" in argv or "--" in argv:
        raise _InvalidArguments()
    try:
        parsed = parser.parse_args(argv)
    except argparse.ArgumentError:
        raise _InvalidArguments() from None
    for values in (parsed.packet_dir, parsed.index_sha256):
        if len(values) != 1 or not values[0].strip():
            raise _InvalidArguments()
    return parsed.packet_dir[0], parsed.index_sha256[0]


def _json_line(stream, value):
    # The frozen summary and error codes contain only ASCII, also valid UTF-8.
    print(json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
          file=stream, flush=True)


def main(argv=None) -> int:
    """Return 0/1/2/130; print only the frozen summary or a fixed error object."""
    try:
        arguments = list(sys.argv[1:] if argv is None else argv)
        parser = _parser()
        if arguments == ["--help"]:
            parser.print_help(file=sys.stdout)
            return 0
        packet_dir, expected = _arguments(parser, arguments)
        summary = audit_control_packet(packet_dir, expected_index_sha256=expected)
        _json_line(sys.stdout, summary)
        return 0
    except _InvalidArguments:
        code, status = "packet_cli_invalid_argument", 2
    except ControlPacketAuditError as error:
        code, status = ((error.code, 1) if isinstance(error.code, str) and error.code in _AUDIT_CODES
                        else ("packet_cli_internal_error", 1))
    except KeyboardInterrupt:
        code, status = "packet_cli_interrupted", 130
    except Exception:
        code, status = "packet_cli_internal_error", 1
    try:
        _json_line(sys.stderr, {"error": code})
    except Exception:
        # A closed/unwritable error stream cannot carry JSON; never add a traceback.
        pass
    return status


if __name__ == "__main__":
    raise SystemExit(main())

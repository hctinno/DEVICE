"""Plan by default; --execute copies one explicitly allow-listed workspace."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labflow.workspace_archive import ArchiveError, archive_workspace, prepare_workspace, load_archive_document, lookup_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path,
                        help="JSON {sources:[{root,base_manifest,base_sha256,ads_manifest,ads_sha256}],protected_roots:[]}")
    parser.add_argument("--scope-sha256", help="Required with --execute; pin the reviewed allow-list bytes")
    parser.add_argument("--root")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-map", type=Path, help="JSON list of from/to/evidence/evidence_sha256 mappings")
    parser.add_argument("--git-evidence", type=Path, help="JSON {path,sha256}; independent report, no deletion grant")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--lookup", help="Original absolute reference; metadata-only, no execution authority")
    parser.add_argument("--stream", help="Named $DATA suffix used with --lookup")
    parser.add_argument("--manifest-sha256", help="Select an unambiguous historical base catalog with --lookup")
    args = parser.parse_args()
    try:
        if args.lookup is not None:
            if args.execute or args.scope or args.root or args.source_map or args.git_evidence or args.scope_sha256:
                raise ArchiveError("workspace_archive_lookup_mode_conflict")
            result = lookup_archive(args.archive, args.lookup, stream_name=args.stream,
                                    manifest_sha256=args.manifest_sha256)
            print(json.dumps(result, ensure_ascii=True, sort_keys=True))
            return 0
        if args.scope is None or args.root is None or args.stream or args.manifest_sha256:
            raise ArchiveError("workspace_archive_copy_arguments")
        if args.execute and args.scope_sha256 is None:
            raise ArchiveError("workspace_archive_scope_pin_required")
        scope = load_archive_document(args.scope, expected_sha256=args.scope_sha256)
        archive_root = scope.get("archive_root")
        if archive_root is None or str(Path(archive_root)).casefold() != str(args.archive).casefold():
            raise ArchiveError("workspace_archive_archive_destination_not_pinned")
        sources = scope["sources"]
        selected = [row for row in sources if str(Path(row["root"])).casefold() == str(Path(args.root)).casefold()]
        if len(selected) != 1 or len({str(Path(row["root"])).casefold() for row in sources}) != len(sources):
            raise ArchiveError("workspace_archive_scope_selection")
        settings = dict(allow_roots=[row["root"] for row in sources],
                        protected_roots=scope.get("protected_roots", []),
                        native_preserved_roots=scope.get("native_preserved_roots", []),
                        source_mappings=load_archive_document(args.source_map) if args.source_map else [])
        if args.execute:
            result = archive_workspace(selected[0], args.archive, **settings,
                                       git_evidence=load_archive_document(args.git_evidence) if args.git_evidence else None,
                                       scope_evidence=dict(path=str(args.scope.absolute()), sha256=args.scope_sha256),
                                       archive_roots=[archive_root])
        else:
            result = prepare_workspace(selected[0], **settings).summary()
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except (ArchiveError, OSError, ValueError, KeyError, TypeError):
        print(json.dumps(dict(error="workspace_archive_rejected", executed=args.execute,
                              deletion_authorized=False)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

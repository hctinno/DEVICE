"""Real, disposable CAS fixtures; no original workspaces or model processes."""
import hashlib
import base64
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch

try:
    from labflow import workspace_archive as archive
except ImportError:
    archive = None

_DEVELOPMENT = next((p for p in Path(__file__).absolute().parents
                     if p.name.casefold() == "development" and p.parent.name.casefold() == ".local"), None)
EVIDENCE = (_DEVELOPMENT / "runs/migration-20261031/cas" if _DEVELOPMENT
            else Path(tempfile.gettempdir()) / "dgm-workspace-archive-tests")


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while data := stream.read(1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def info(path):
    value = path.stat()
    return dict(st_dev=value.st_dev, st_ino=value.st_ino, bytes=value.st_size,
                mtime_ns=value.st_mtime_ns, nlink=value.st_nlink,
                mode=value.st_mode, file_attributes=getattr(value, "st_file_attributes", 0),
                acl={"status": "read", "sddl": "synthetic-opaque-owner-group-dacl"})


def jsonl(path, values):
    with open(path, "x", encoding="utf-8", newline="\n") as stream:
        for value in values:
            stream.write(json.dumps(value, sort_keys=True) + "\n")


def extended(path):
    return "\\\\?\\" + str(path) if os.name == "nt" else str(path)


def junction(link, target):
    if os.name == "nt":
        command = "New-Item -ItemType Junction -Path '" + str(link).replace("'", "''") + "' -Target '" + str(target).replace("'", "''") + "' | Out-Null"
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], check=True,
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        os.symlink(target, link, target_is_directory=True)


class WorkspaceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(archive, "workspace CAS implementation is missing")
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=EVIDENCE)
        self.home = Path(self.temp.name)
        self.assertTrue(self.home.is_relative_to(EVIDENCE))
        self.addCleanup(self.cleanup)
        self.source = self.home / "original"
        self.source.mkdir()
        (self.source / ".git/objects").mkdir(parents=True)
        (self.source / ".local").mkdir()
        (self.source / ".local/failure.log").write_bytes(b"original synthetic failure\n")
        (self.source / ".git/objects/object").write_bytes(b"same synthetic bytes\n")
        (self.source / "WIP.py").write_bytes(b"same synthetic bytes\n")
        self.destination = self.home / "archive"

    def cleanup(self):
        target = self.home.absolute()
        if not target.is_relative_to(EVIDENCE.absolute()):
            raise AssertionError("fixture cleanup escaped approved run root")
        if target.exists():
            shutil.rmtree(extended(target))
        self.temp.cleanup()

    def catalog(self, *, ads=None, reparse=False, mutate=None, version="first"):
        ads = ads or {}
        if reparse:
            target = self.home / "link-target"
            target.mkdir()
            (target / "never-read").write_bytes(b"outside-catalog-synthetic\n")
            junction(self.source / "historical-link", target)
        for relative, streams in ads.items():
            for name, payload in streams.items():
                with open(str(self.source if relative == "." else self.source / relative) + name, "wb") as stream:
                    stream.write(payload)
        entries = []
        directories = []
        source_access = Path(extended(self.source))
        for parent, names, files in os.walk(source_access):
            directory = Path(parent)
            names[:] = [name for name in names if not getattr((directory / name).lstat(), "st_file_attributes", 0) & 0x400
                        and not (directory / name).is_symlink()]
            relative = directory.relative_to(source_access).as_posix()
            directories.append(relative)
            entries.append(dict(record="entry", path=relative, kind="directory", **info(directory)))
            for name in files:
                path = directory / name
                relative_file = path.relative_to(source_access).as_posix()
                entries.append(dict(record="entry", path=relative_file, kind="file", sha256=sha(path),
                                    unstable=False, after=info(path), **info(path)))
        if reparse:
            link_info = (self.source / "historical-link").lstat()
            entries.append(dict(record="entry", path="historical-link", kind="reparse", bytes=0,
                                st_dev=link_info.st_dev, st_ino=link_info.st_ino, mtime_ns=link_info.st_mtime_ns, target="synthetic-target",
                                reparse_tag=getattr(link_info, "st_reparse_tag", 0),
                                target_identity={"st_dev": 1, "st_ino": 10}, physical_resolve="synthetic-target"))
        if mutate:
            mutate(entries)
        counts = dict(files=sum(e["kind"] == "file" for e in entries),
                      directories=len(directories), reparses=int(reparse),
                      bytes=sum(e["bytes"] for e in entries if e["kind"] == "file"), errors=0, unstable=0)
        base = self.home / ("base-" + version + ".jsonl")
        values = [dict(record="header", schema="autolab-preservation-catalog-v1", root=str(self.source))]
        values += entries
        values += [dict(record="directory_end", path=p, unstable=False) for p in directories]
        values += [dict(record="footer", complete=True, **counts)]
        jsonl(base, values)
        extra = self.home / ("ads-" + version + ".jsonl")
        values = [dict(record="header", schema="autolab-preservation-ads-v1", logical_root=str(self.source),
                       base_manifest_sha256=sha(base))]
        stream_count = stream_bytes = 0
        for entry in entries:
            relative = entry["path"]
            streams = []
            for name, payload in ads.get(relative, {}).items():
                stream = dict(name=name, bytes=len(payload), enumerated_bytes=len(payload),
                              sha256=hashlib.sha256(payload).hexdigest(), unstable=False,
                              opened_before=info(Path(str(self.source if relative == "." else self.source / relative) + name)),
                              opened_after=info(Path(str(self.source if relative == "." else self.source / relative) + name)))
                values.append(dict(record="stream", path=relative, **stream))
                streams.append(stream)
                stream_count += 1
                stream_bytes += len(payload)
            values.append(dict(record="entry", path=relative, kind=entry["kind"], streams=streams,
                               unstable=False, baseline_size_mtime_match=True,
                               ads_status="unknown_reparse_not_followed" if entry["kind"] == "reparse"
                               else ("named_ads_hashed" if streams else "no_named_ads_confirmed")))
        values += [dict(record="footer", complete=not reparse, entries=len(entries), named_streams=stream_count,
                        named_stream_bytes=stream_bytes, unknown=int(reparse), reparse_unassessed=int(reparse),
                        errors=0, unstable=0, baseline_mismatch=0)]
        jsonl(extra, values)
        return dict(root=str(self.source), base_manifest=str(base), base_sha256=sha(base),
                    ads_manifest=str(extra), ads_sha256=sha(extra))

    def execute(self, spec, **kwargs):
        return archive.archive_workspace(spec, self.destination, allow_roots=[str(self.source)], **kwargs)

    def test_stores_actual_git_wip_and_failure_bytes_and_deduplicates(self):
        spec = self.catalog()
        result = self.execute(spec)
        self.assertTrue(result["data_complete"])
        self.assertFalse(result["deletion_authorized"])
        self.assertEqual(result["files_verified"], 3)
        self.assertEqual(result["unique_data_blobs"], 2)
        for payload in (b"same synthetic bytes\n", b"original synthetic failure\n"):
            digest = hashlib.sha256(payload).hexdigest()
            self.assertEqual(sha(self.destination / "objects/sha256" / digest[:2] / digest), digest)
        self.assertEqual(sha(self.destination / "manifests/sha256" / spec["base_sha256"]), spec["base_sha256"])
        self.assertTrue((self.source / ".local/failure.log").exists())

    def test_resume_rechecks_existing_blobs_and_rejects_corruption(self):
        spec = self.catalog()
        self.execute(spec)
        again = self.execute(spec)
        self.assertTrue(again["data_complete"])
        digest = hashlib.sha256(b"same synthetic bytes\n").hexdigest()
        blob = self.destination / "objects/sha256" / digest[:2] / digest
        blob.write_bytes(b"corrupt")
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec)
        self.assertEqual(blob.stat().st_size, 7)

    def test_rejects_changed_source_even_when_the_old_blob_exists(self):
        spec = self.catalog()
        self.execute(spec)
        (self.source / "WIP.py").write_bytes(b"different current bytes\n")
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec)

    def test_manifest_pin_footer_coverage_and_scope_fail_before_archive_creation(self):
        spec = self.catalog()
        cases = [dict(spec, base_sha256="0" * 64), dict(spec, root=str(self.home / "other"))]
        for bad in cases:
            with self.subTest(bad=bad["root"]), self.assertRaises(archive.ArchiveError):
                self.execute(bad)
        self.assertFalse(self.destination.exists())

    def test_relative_traversal_and_device_basenames_fail_closed(self):
        spec = self.catalog(mutate=lambda entries: entries[1].update(path="../escape"))
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec)
        self.assertFalse(self.destination.exists())
        for path in ["C:/escape", "a\\b", "a/../b", "NUL.txt", "CONIN$", "LPT¹.txt", "file:secret", "a.", "a//b"]:
            with self.subTest(path=path), self.assertRaises(archive.ArchiveError):
                archive.validate_relative_path(path)

    def test_reparse_unknown_is_retained_and_never_claimed_complete(self):
        spec = self.catalog(reparse=True)
        result = self.execute(spec)
        self.assertFalse(result["data_complete"])
        self.assertFalse(result["deletion_authorized"])
        self.assertEqual(result["unresolved_reparse"], ["historical-link"])

    @unittest.skipUnless(os.name == "nt", "NTFS named streams require Windows")
    def test_file_and_directory_ads_are_real_separate_verified_blobs(self):
        payloads = {"WIP.py": {":proof:$DATA": b"named-file-proof\n"},
                    ".": {":directory-proof:$DATA": b"named-directory-proof\n"}}
        spec = self.catalog(ads=payloads)
        result = self.execute(spec)
        self.assertTrue(result["data_complete"])
        self.assertEqual(result["ads_streams_verified"], 2)
        for stream_map in payloads.values():
            for payload in stream_map.values():
                digest = hashlib.sha256(payload).hexdigest()
                self.assertEqual(sha(self.destination / "objects/sha256" / digest[:2] / digest), digest)

    def test_cli_defaults_to_plan_without_copying(self):
        spec = self.catalog()
        scope = self.home / "scope.json"
        scope.write_text(json.dumps(dict(sources=[spec], protected_roots=[])), encoding="utf-8")
        command = [sys.executable, "-B", str(Path(__file__).parents[1] / "scripts/archive_development_workspace.py"),
                   "--scope", str(scope), "--root", str(self.source), "--archive", str(self.destination)]
        process = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertFalse(self.destination.exists())
        self.assertFalse(json.loads(process.stdout)["executed"])

    def test_source_native_before_after_is_preserved_in_the_copy_journal(self):
        spec = self.catalog()
        result = self.execute(spec)
        records = [json.loads(line) for line in (self.destination / result["journal_relative"]).read_text(encoding="utf-8").splitlines()]
        entry = next(row for row in records if row.get("record") == "file")
        self.assertEqual(entry["source_before"], entry["source_after"])
        self.assertEqual(entry["source_before"]["st_ino"], (self.source / entry["path"]).stat().st_ino)

    def test_inconsistent_ads_footer_is_rejected_before_copying(self):
        spec = self.catalog(reparse=True)
        path = Path(spec["ads_manifest"])
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows[-1]["complete"] = True
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        spec["ads_sha256"] = sha(path)
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec)
        self.assertFalse(self.destination.exists())

    def moved_sdk(self, storage="copy"):
        sdk = self.source / ".local/android-runtime"
        sdk.mkdir()
        (sdk / "sdk.bin").write_bytes(b"synthetic-sdk-bytes\n")
        spec = self.catalog()
        identity = {key: info(sdk)[key] for key in ("st_dev", "st_ino")}
        target = self.home / "managed-toolchain"
        sdk.rename(target)
        proof = self.home / "native-move.json"
        proof.write_text(json.dumps(dict(operation="native-move", status="complete", **{"from": str(sdk), "to": str(target)},
                                         before_identity=identity, after_identity=identity)), encoding="utf-8")
        mapping = {"from": str(sdk), "to": str(target), "evidence": str(proof), "evidence_sha256": sha(proof),
                   "allow_directory_mtime": [".local"], "storage": storage}
        return spec, mapping, target

    def test_moved_sdk_uses_pinned_native_proof_and_only_parent_directory_mtime_exception(self):
        spec, mapping, target = self.moved_sdk()
        result = self.execute(spec, source_mappings=[mapping])
        self.assertTrue(result["data_complete"])
        digest = hashlib.sha256(b"synthetic-sdk-bytes\n").hexdigest()
        self.assertEqual(sha(self.destination / "objects/sha256" / digest[:2] / digest), digest)
        self.assertTrue((target / "sdk.bin").exists())

    def test_native_preserved_requires_separate_exact_allowlist_and_is_not_cas_complete(self):
        spec, mapping, target = self.moved_sdk("native-preserved")
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec, source_mappings=[mapping])
        result = self.execute(spec, source_mappings=[mapping], native_preserved_roots=[mapping["from"]])
        self.assertFalse(result["data_complete"])
        self.assertFalse(result["cas_self_contained"])
        self.assertTrue(result["managed_development_required"])
        self.assertEqual(result["native_reference_count"], 1)
        digest = hashlib.sha256(b"synthetic-sdk-bytes\n").hexdigest()
        self.assertFalse((self.destination / "objects/sha256" / digest[:2] / digest).exists())
        (target / "sdk.bin").write_bytes(b"changed-sdk\n")
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec, source_mappings=[mapping], native_preserved_roots=[mapping["from"]])

    def test_long_source_paths_are_read_by_native_extended_path(self):
        path = Path(extended(self.source / ("a" * 100) / ("b" * 100)))
        path.mkdir(parents=True)
        (path / "long.bin").write_bytes(b"long-native-path\n")
        self.assertGreater(len(str(path / "long.bin")), 260)
        spec = self.catalog()
        result = self.execute(spec)
        self.assertEqual(result["files_verified"], 4)

    def test_change_during_real_native_read_fails_and_keeps_failure_journal(self):
        spec = self.catalog()
        reader = archive._reader
        source = self.source / "WIP.py"
        changed = False
        @contextmanager
        def injected(path, **kwargs):
            nonlocal changed
            with reader(path, **kwargs) as (stream, current, before):
                if Path(path) == source and not kwargs.get("metadata"):
                    class Stream:
                        def read(self, size):
                            nonlocal changed
                            data = stream.read(size)
                            if data and not changed:
                                changed = True
                                current_stat = source.stat()
                                os.utime(source, ns=(current_stat.st_atime_ns, current_stat.st_mtime_ns + 1000000000))
                            return data
                    yield Stream(), current, before
                else:
                    yield stream, current, before
        with patch.object(archive, "_reader", injected), self.assertRaises(archive.ArchiveError):
            self.execute(spec)
        records = [json.loads(line) for path in (self.destination / "receipts").glob("*.jsonl")
                   for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[-1]["record"], "failure")
        self.assertFalse(records[-1]["complete"])
        self.assertEqual(records[-1]["context"]["path"], "WIP.py")

    def test_cli_execute_requires_the_reviewed_scope_pin(self):
        spec = self.catalog()
        scope = self.home / "scope.json"
        scope.write_text(json.dumps(dict(sources=[spec], protected_roots=[])), encoding="utf-8")
        command = [sys.executable, "-B", str(Path(__file__).parents[1] / "scripts/archive_development_workspace.py"),
                   "--scope", str(scope), "--root", str(self.source), "--archive", str(self.destination), "--execute"]
        rejected = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)
        self.assertFalse(self.destination.exists())
        accepted = subprocess.run(command + ["--scope-sha256", sha(scope)], capture_output=True, text=True)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertTrue(json.loads(accepted.stdout)["data_complete"])

    def test_move_proof_itself_is_preserved_in_the_archive(self):
        spec, mapping, _ = self.moved_sdk()
        self.execute(spec, source_mappings=[mapping])
        self.assertEqual(sha(self.destination / "evidence/sha256" / mapping["evidence_sha256"]), mapping["evidence_sha256"])

    def test_interrupted_fsync_keeps_pending_and_resume_reverifies_bytes(self):
        spec = self.catalog()
        with patch.object(archive.os, "fsync", side_effect=OSError("synthetic interrupted fsync")):
            with self.assertRaises(archive.ArchiveError):
                self.execute(spec)
        pending = list(self.destination.rglob("*.pending"))
        self.assertTrue(pending)
        result = self.execute(spec)
        self.assertTrue(result["data_complete"])
        self.assertTrue(all(path.exists() for path in pending))

    def test_untracked_current_files_and_ads_are_not_silently_lost(self):
        spec = self.catalog()
        before = self.source.stat()
        (self.source / "new-untracked.txt").write_bytes(b"new synthetic content\n")
        os.utime(self.source, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec)

    def test_output_junction_and_moved_file_mtime_exceptions_are_rejected(self):
        spec, mapping, _ = self.moved_sdk()
        mapping["allow_directory_mtime"] = [".local/failure.log"]
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec, source_mappings=[mapping])
        self.assertFalse(self.destination.exists())
        target = self.home / "outside-output"
        target.mkdir()
        junction(self.destination, target)
        with self.assertRaises(archive.ArchiveError):
            self.execute(spec)
        self.assertFalse(list(target.iterdir()))

    def test_multi_chunk_default_and_fifteen_named_streams_preserve_all_bytes(self):
        digest = hashlib.sha256()
        large = self.source / "large.bin"
        with open(large, "wb") as output:
            for data in (b"A" * 1048576, b"B" * 1048576, b"last-seven"):
                output.write(data)
                digest.update(data)
        payloads = {f":stream{i}:$DATA": bytes([65 + i]) * 50 for i in range(15)} if os.name == "nt" else {}
        spec = self.catalog(ads={"WIP.py": payloads})
        result = self.execute(spec)
        self.assertTrue(result["data_complete"])
        self.assertEqual(result["ads_streams_verified"], len(payloads))
        self.assertEqual(result["ads_bytes_verified"], sum(map(len, payloads.values())))
        value = digest.hexdigest()
        self.assertEqual(sha(self.destination / "objects/sha256" / value[:2] / value), value)
        for payload in payloads.values():
            value = hashlib.sha256(payload).hexdigest()
            self.assertEqual(sha(self.destination / "objects/sha256" / value[:2] / value), value)

    def test_native_reparse_move_proof_does_not_upgrade_unknown(self):
        spec = self.catalog(reparse=True)
        source = self.source / "historical-link"
        initial = source.lstat()
        identity = dict(st_dev=initial.st_dev, st_ino=initial.st_ino)
        moved = self.home / "preserved-original-reparse"
        source.rename(moved)
        proof = self.home / "link-move-proof.json"
        proof.write_text(json.dumps(dict(operation="native-move", status="complete", **{"from": str(source), "to": str(moved)},
                                         before_identity=identity, after_identity=identity)), encoding="utf-8")
        mapping = {"from": str(source), "to": str(moved), "evidence": str(proof), "evidence_sha256": sha(proof),
                   "allow_directory_mtime": ["."]}
        result = self.execute(spec, source_mappings=[mapping])
        self.assertFalse(result["data_complete"])
        self.assertEqual(result["unresolved_reparse"], ["historical-link"])
        self.assertEqual(moved.lstat().st_ino, initial.st_ino)
        value = archive.lookup_archive(self.destination, source)
        self.assertEqual(value["kind"], "reparse-metadata-ads-unknown")
        self.assertEqual(Path(value["storage_path"]), moved)
        self.assertFalse(value["execution_authority"])

    def test_pinned_external_git_report_is_archived_without_granting_deletion(self):
        spec = self.catalog()
        report = self.home / "git-report.json"
        report.write_text('{"status":"synthetic-separate-report"}\n', encoding="utf-8")
        result = self.execute(spec, git_evidence=dict(path=str(report), sha256=sha(report)))
        self.assertEqual(sha(self.destination / "evidence/sha256" / sha(report)), sha(report))
        self.assertFalse(result["deletion_authorized"])
        self.assertEqual(result["git_preservation_status"], "external_report_attached_not_adjudicated")

    def test_original_native_reparse_report_schema_links_only_immediate_parent_change(self):
        spec = self.catalog(reparse=True)
        source = self.source / "historical-link"
        before = source.lstat()
        parent = self.source.stat()
        destination = self.home / "saved-link"
        source.rename(destination)
        raw = b"synthetic opaque reparse buffer"
        snapshot = dict(device=before.st_dev, inode=before.st_ino, mtime_ns=before.st_mtime_ns,
                        tag=getattr(before, "st_reparse_tag", 0), attributes=getattr(before, "st_file_attributes", 0),
                        raw_sha256=hashlib.sha256(raw).hexdigest(), raw_base64=base64.b64encode(raw).decode(), target="synthetic-target")
        evidence = self.home / "native-links-after.json"
        evidence.write_text(json.dumps(dict(rows=[dict(source=str(source), destination=str(destination),
            root=str(self.source), relative="historical-link", before=snapshot, after=snapshot,
            changed_source_directories=[dict(relative=".", device=parent.st_dev, inode=parent.st_ino,
                mtime_ns=parent.st_mtime_ns, after_mtime_ns=self.source.stat().st_mtime_ns)])])), encoding="utf-8")
        mapping = {"from": str(source), "to": str(destination), "evidence_kind": "native-reparse-report",
                   "evidence": str(evidence), "evidence_sha256": sha(evidence), "allow_directory_mtime": ["."]}
        result = self.execute(spec, source_mappings=[mapping])
        self.assertEqual(result["unresolved_reparse"], ["historical-link"])
        self.assertFalse(result["data_complete"])

    def test_original_sdk_before_after_and_atomic_move_reports_are_consumed_unchanged(self):
        spec, mapping, target = self.moved_sdk("native-preserved")
        root_info = info(target)
        file_info = info(target / "sdk.bin")
        entries = [dict(path=".", kind="directory", dev=root_info["st_dev"], ino=root_info["st_ino"],
                        mtime_ns=root_info["mtime_ns"], nlink=root_info["nlink"]),
                   dict(path="sdk.bin", kind="file", dev=file_info["st_dev"], ino=file_info["st_ino"],
                        mtime_ns=file_info["mtime_ns"], nlink=file_info["nlink"], bytes=file_info["bytes"], sha256=sha(target / "sdk.bin"))]
        before, after, atomic = [self.home / name for name in ("android-before.json", "android-after-move.json", "atomic-move-result.json")]
        before.write_text(json.dumps(dict(root=mapping["from"], entries=entries)), encoding="utf-8")
        after.write_text(json.dumps(dict(root=str(target), entries=entries)), encoding="utf-8")
        atomic.write_text(json.dumps(dict(moves=[dict(kind="android", source=mapping["from"], target=str(target),
            operation="same_volume_os_rename", before_after_sha_native_id_mtime_equal=True,
            files=1, directories=1, bytes=file_info["bytes"], source_absent=True, target_present=True)])), encoding="utf-8")
        mapping.update(evidence_kind="native-sdk-move", evidence=str(atomic), evidence_sha256=sha(atomic),
                       before_evidence=dict(path=str(before), sha256=sha(before)), after_evidence=dict(path=str(after), sha256=sha(after)))
        result = self.execute(spec, source_mappings=[mapping], native_preserved_roots=[mapping["from"]])
        self.assertFalse(result["cas_self_contained"])
        self.assertEqual(result["native_reference_bytes"], len(b"synthetic-sdk-bytes\n"))
        for artifact in (before, after, atomic):
            self.assertEqual(sha(self.destination / "evidence/sha256" / sha(artifact)), sha(artifact))

    def test_lookup_survives_missing_source_and_exposes_metadata_only(self):
        spec = self.catalog()
        self.execute(spec)
        original = self.source / "WIP.py"
        shutil.rmtree(extended(self.source))
        value = archive.lookup_archive(self.destination, original)
        self.assertEqual(set(value), {"original_ref", "kind", "sha", "bytes", "storage_path", "execution_authority"})
        self.assertFalse(value["execution_authority"])
        self.assertEqual(value["sha"], hashlib.sha256(b"same synthetic bytes\n").hexdigest())
        self.assertEqual(sha(Path(value["storage_path"])), value["sha"])
        directory = archive.lookup_archive(self.destination, self.source)
        self.assertEqual(directory["kind"], "directory-metadata")
        self.assertEqual(directory["sha"], spec["base_sha256"])
        command = [sys.executable, "-B", str(Path(__file__).parents[1] / "scripts/archive_development_workspace.py"),
                   "--archive", str(self.destination), "--lookup", str(original)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), value)

    def test_lookup_native_preserved_is_not_an_executable_alias(self):
        spec, mapping, target = self.moved_sdk("native-preserved")
        self.execute(spec, source_mappings=[mapping], native_preserved_roots=[mapping["from"]])
        original = Path(mapping["from"]) / "sdk.bin"
        shutil.rmtree(extended(self.source))
        value = archive.lookup_archive(self.destination, original)
        self.assertEqual(value["kind"], "native-preserved-file")
        self.assertEqual(Path(value["storage_path"]), target / "sdk.bin")
        self.assertFalse(value["execution_authority"])

    def test_lookup_requires_a_manifest_pin_when_historical_snapshots_differ(self):
        first = self.catalog()
        self.execute(first)
        (self.source / "WIP.py").write_bytes(b"second independent snapshot\n")
        second = self.catalog(version="second")
        self.execute(second)
        original = self.source / "WIP.py"
        with self.assertRaises(archive.ArchiveError):
            archive.lookup_archive(self.destination, original)
        one = archive.lookup_archive(self.destination, original, manifest_sha256=first["base_sha256"])
        two = archive.lookup_archive(self.destination, original, manifest_sha256=second["base_sha256"])
        self.assertNotEqual(one["sha"], two["sha"])

    @unittest.skipUnless(os.name == "nt", "NTFS named stream lookup requires Windows")
    def test_lookup_named_stream_returns_only_its_pinned_blob_metadata(self):
        payload = b"synthetic named history\n"
        spec = self.catalog(ads={"WIP.py": {":proof:$DATA": payload}})
        self.execute(spec)
        original = self.source / "WIP.py"
        shutil.rmtree(extended(self.source))
        value = archive.lookup_archive(self.destination, original, stream_name=":proof:$DATA")
        self.assertEqual(value["kind"], "ads")
        self.assertEqual(value["sha"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(value["bytes"], len(payload))
        self.assertFalse(value["execution_authority"])


if __name__ == "__main__":
    unittest.main()

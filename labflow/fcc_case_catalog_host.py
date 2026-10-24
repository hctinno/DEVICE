"""Explicit Windows startup-only loading of genuine, source-checked FCC cases.

No server, database, discovery, writes, hardware, model, or reload lives here.
"""
import json
import hashlib
from pathlib import Path
import re

from . import control_packet_prepare as _native
from . import fcc_report_cases as _cases


_MIB = 1024 * 1024
_CONFIG_BYTES = 64 * 1024
_RECEIPT_BYTES = 8 * _MIB
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_PATH_TYPE = type(Path())
_CODES = frozenset({"fcc_case_host_invalid_argument", "fcc_case_host_path_invalid", "fcc_case_host_unavailable",
                    "fcc_case_host_pin_mismatch", "fcc_case_host_input_changed", "fcc_case_host_backend_unavailable"})


class FccCaseCatalogHostError(ValueError):
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else "fcc_case_host_invalid_argument"
        super().__init__(self.code)


def _fail(code):
    raise FccCaseCatalogHostError(code)


def _limit():
    raise _cases.FccReportCaseError("fcc_case_limit_exceeded")


def _hash(value):
    if type(value) is not str or not _HASH.fullmatch(value):
        _fail("fcc_case_host_invalid_argument")


def _path(value, suffix, *, config=False):
    if type(value) is not str and not (config and type(value) is _PATH_TYPE):
        _fail("fcc_case_host_invalid_argument")
    path = Path(value)
    if not path.is_absolute() or path.suffix.lower() != suffix:
        _fail("fcc_case_host_path_invalid")
    try:
        return _native._local_path(str(path))
    except _native.ControlPacketPrepareError:
        _fail("fcc_case_host_path_invalid")


def _descriptor(value, suffix, cap):
    if type(value) is not dict or set(value) != {"path", "sha256", "bytes"}:
        _fail("fcc_case_host_invalid_argument")
    _hash(value["sha256"])
    if type(value["bytes"]) is not int or value["bytes"] < 1:
        _fail("fcc_case_host_invalid_argument")
    if value["bytes"] > cap:
        _limit()
    return {**value, "path": _path(value["path"], suffix)}


def _config(raw):
    try:
        value = _cases._plain(_cases._decode(raw, byte_limit=_CONFIG_BYTES), byte_limit=_CONFIG_BYTES,
                              depth_limit=8, node_limit=2048)
    except _cases.FccReportCaseError as error:
        if error.code == "fcc_case_limit_exceeded":
            raise
        _fail("fcc_case_host_invalid_argument")
    keys = {"schema_version", "kind", "manifest", "packet", "page_scope", "packet_path", "page_scope_path", "pdf_sources"}
    if (type(value) is not dict or set(value) != keys or type(value["schema_version"]) is not int
            or value["schema_version"] != 1 or value["kind"] != "fcc_case_catalog_host_input"
            or type(value["pdf_sources"]) is not list):
        _fail("fcc_case_host_invalid_argument")
    if len(value["pdf_sources"]) > 16:
        _limit()
    for selector in ("packet_path", "page_scope_path"):
        _cases._preparation_path(value[selector], json_only=True)
    for role, cap in (("manifest", _MIB), ("packet", 4 * _MIB), ("page_scope", 64 * 1024)):
        value[role] = _descriptor(value[role], ".json", cap)
    rows, hashes, total = [], set(), 0
    for row in value["pdf_sources"]:
        row = _descriptor(row, ".pdf", 16 * _MIB)
        if row["sha256"] in hashes:
            raise _cases.FccReportCaseError("fcc_case_invalid_sources")
        hashes.add(row["sha256"]); total += row["bytes"]; rows.append(row)
        if total > 64 * _MIB:
            _limit()
    value["pdf_sources"] = rows
    return value


class _PinnedInputs:
    def __init__(self, backend):
        self.backend, self.records, self.identities = backend, [], set()

    def read(self, path, role, sha, cap, expected_size=None):
        tree = _native._Tree(path.parent, self.backend)
        before = tree.file_stat(path)
        if before.st_size > cap:
            _limit()
        if expected_size is not None and before.st_size != expected_size:
            _fail("fcc_case_host_pin_mismatch")
        stamp = _native._stamp(before)
        identity = (role, before.st_dev, before.st_ino)
        if identity in self.identities:
            _fail("fcc_case_host_path_invalid")
        descriptor = self.backend.open_read(path, pin=True)
        if (_native._stamp(self.backend.info(descriptor, directory=False)) != stamp
                or _native._stamp(tree.file_stat(path)) != stamp):
            _fail("fcc_case_host_input_changed")
        blob = _native._read_descriptor(descriptor, cap, "packet_prepare_copy_failed")
        if len(blob) != before.st_size:
            _fail("fcc_case_host_input_changed")
        if hashlib.sha256(blob).hexdigest() != sha:
            _fail("fcc_case_host_pin_mismatch")
        if (_native._stamp(self.backend.info(descriptor, directory=False)) != stamp
                or _native._stamp(tree.file_stat(path)) != stamp):
            _fail("fcc_case_host_input_changed")
        self.identities.add(identity)
        self.records.append({"path": path, "tree": tree, "descriptor": descriptor, "stamp": stamp,
                             "role": role, "sha256": sha, "cap": cap})
        return blob

    def descriptor(self, value, role, cap):
        return self.read(value["path"], role, value["sha256"], cap, value["bytes"])

    def verify(self):
        for row in self.records:
            descriptor, stamp = row["descriptor"], row["stamp"]
            if (_native._stamp(self.backend.info(descriptor, directory=False)) != stamp
                    or _native._stamp(row["tree"].file_stat(row["path"])) != stamp):
                _fail("fcc_case_host_input_changed")
            raw = _native._read_descriptor(descriptor, row["cap"], "packet_prepare_source_changed")
            if len(raw) != stamp[2] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                _fail("fcc_case_host_input_changed")
            if (_native._stamp(self.backend.info(descriptor, directory=False)) != stamp
                    or _native._stamp(row["tree"].file_stat(row["path"])) != stamp):
                _fail("fcc_case_host_input_changed")

    def receipt(self):
        return [{"role": row["role"], "sha256": row["sha256"], "bytes": row["stamp"][2],
                 "identity": list(row["stamp"][:2]), "mtime_ns": row["stamp"][3], "mode": row["stamp"][4]}
                for row in sorted(self.records, key=lambda value: (value["role"], value["sha256"]))]


def _receipt(catalog, prepared, inputs, pin):
    summary = _cases.FccReportCaseCatalog.summary(catalog)
    evidence_count = 0
    for preview in summary["case_previews"]:
        detail = _cases.FccReportCaseCatalog.case(catalog, preview["case_id"])
        evidence_count += sum(evidence["literal_verified"] is True
                              for claim in detail["case"]["claims"] for evidence in claim["evidence"])
    scopes, citable = [], 0
    for document in sorted(summary["documents"], key=lambda row: row["document_id"]):
        scope = prepared["page_scope"]["sources"][document["sha256"]]
        citable += sum(page["citable"] for page in document["page_index"])
        scopes.append({"document_id": document["document_id"], "source_sha256": document["sha256"],
                       "mode": scope["mode"], "basis_id": scope["basis_id"], "basis_sha256": scope["basis_sha256"],
                       "requested_pages": scope["pages"], "extraction": document["extraction"], "page_index": document["page_index"]})
    result = {"schema_version": 1, "kind": "fcc_case_catalog_host_load", "config_sha256": pin,
              "metadata_preparation": {key: prepared[key] for key in ("provenance", "verification")},
              "inputs": inputs.receipt(), "page_scopes": scopes,
              "construction": {"catalog_type_exact": True, "document_count": len(summary["documents"]),
                               "case_count": len(summary["case_previews"]), "citable_page_count": citable,
                               "verified_evidence_literal_count": evidence_count},
              "verification": dict.fromkeys(("authority_or_rights_verified", "hardware_verified",
                  "normative_compliance_verified", "currentness_verified", "execution_authorized"), False)}
    raw = _cases._canonical(result)
    if len(raw) > _RECEIPT_BYTES:
        _limit()
    return json.loads(raw)


def load_fcc_case_catalog(config_path, *, expected_config_sha256):
    """Return (genuine catalog, detached receipt) after closing all startup pins."""
    backend, failure, result = None, None, None
    try:
        _hash(expected_config_sha256)
        path = _path(config_path, ".json", config=True)
        try:
            backend = _native._WindowsIO()
        except Exception:
            _fail("fcc_case_host_backend_unavailable")
        inputs = _PinnedInputs(backend)
        config = _config(inputs.read(path, "config", expected_config_sha256, _CONFIG_BYTES))
        manifest = inputs.descriptor(config["manifest"], "manifest", _MIB)
        packet = inputs.descriptor(config["packet"], "packet", 4 * _MIB)
        scope = inputs.descriptor(config["page_scope"], "page_scope", 64 * 1024)
        prepared = _cases.prepare_fcc_case_packet(manifest, {config["packet_path"]: packet, config["page_scope_path"]: scope},
            expected_manifest_sha256=config["manifest"]["sha256"], packet_path=config["packet_path"], page_scope_path=config["page_scope_path"])
        expected = {row["sha256"]: row["size_bytes"] for row in prepared["source_refs"]}
        if {row["sha256"]: row["bytes"] for row in config["pdf_sources"]} != expected:
            raise _cases.FccReportCaseError("fcc_case_invalid_sources")
        sources = {row["sha256"]: inputs.descriptor(row, "pdf_source", 16 * _MIB) for row in config["pdf_sources"]}
        catalog = _cases.FccReportCaseCatalog(prepared["packet"], sources, page_scope=prepared["page_scope"])
        if type(catalog) is not _cases.FccReportCaseCatalog:
            _fail("fcc_case_host_unavailable")
        receipt = _receipt(catalog, prepared, inputs, expected_config_sha256)
        inputs.verify()
        result = catalog, receipt
    except FccCaseCatalogHostError as error:
        failure = False, error.code
    except _cases.FccReportCaseError as error:
        failure = True, error.code
    except _native.ControlPacketPrepareError as error:
        code = ("fcc_case_host_path_invalid" if error.code == "packet_prepare_path_invalid" else
                "fcc_case_host_input_changed" if error.code == "packet_prepare_source_changed" else "fcc_case_host_unavailable")
        failure = False, code
    except Exception:
        failure = False, "fcc_case_host_unavailable"
    finally:
        if backend is not None:
            try:
                backend.close()
            except Exception:
                if failure is None:
                    failure = False, "fcc_case_host_unavailable"
    if failure is not None:
        dependency, code = failure
        raise (_cases.FccReportCaseError(code) if dependency else FccCaseCatalogHostError(code)) from None
    return result

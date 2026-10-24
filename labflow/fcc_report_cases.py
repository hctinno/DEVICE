"""Private, detached, read-only HCT FCC report cases with page-local evidence.

Literal validation does not certify a reviewer's interpretation, a legal rule,
institution authenticity, current equipment support, or physical measurements.
"""

from datetime import date, datetime
from functools import wraps
import hashlib
from io import BytesIO
import json
import logging
import math
import re
from urllib.parse import urlsplit

from . import document_extract as _extract
from .control_packet_audit import ControlPacketAuditError, _manifest_path
from .document_extract import ExtractionLimits, extract_document, page_citation


_MIB = 1024 * 1024
_PACKET_BYTES = 4 * _MIB
_PDF_BYTES = 16 * _MIB
_PDF_TOTAL = 64 * _MIB
_OUTPUT_BYTES = 8 * _MIB
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z", re.ASCII)
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_FIELD = re.compile(r"(?:report|issuer|product|method|setting|equipment|correction|result|normative)"
                    r"(?:\.[a-z0-9_]+){1,3}\Z", re.ASCII)
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+09:00\Z", re.ASCII)
_STATUSES = {"reviewed", "extracted", "not_reported", "extraction_failed", "ambiguous", "conflicting"}
_BASES = {"report_fact", "government_rule", "guidance", "standard_reference_only",
          "developer_inference", "synthetic_policy"}
_EVIDENCE = {"document_id", "source_sha256", "file_page", "printed_page", "table", "row", "column",
             "footnotes", "text_sha256", "line_start", "line_end", "quote"}
_CODES = frozenset({"fcc_case_invalid_packet", "fcc_case_invalid_sources", "fcc_case_limit_exceeded",
                    "fcc_case_pdf_invalid", "fcc_case_extraction_unavailable", "fcc_case_invalid_evidence",
                    "fcc_case_invalid_query", "fcc_case_not_found", "fcc_case_invalid_intake"})


class FccReportCaseError(ValueError):
    def __init__(self, code):
        self.code = code if type(code) is str and code in _CODES else "fcc_case_invalid_packet"
        super().__init__(self.code)


def _fail(code="fcc_case_invalid_packet"):
    raise FccReportCaseError(code)


def _public(default):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except FccReportCaseError as error:
                code = error.code
            except Exception:
                code = default
            raise FccReportCaseError(code) from None
        return call
    return decorate


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def _plain(value, *, code="fcc_case_invalid_packet", byte_limit=_PACKET_BYTES, depth_limit=16,
           string_limit=16384, node_limit=50000, detach=True):
    stack, nodes, size = [(value, 0)], 0, 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > node_limit or depth > depth_limit:
            _fail("fcc_case_limit_exceeded")
        kind = type(item)
        if kind is dict:
            if nodes + len(stack) + 2 * len(item) > node_limit:
                _fail("fcc_case_limit_exceeded")
            size += 2 + max(0, 2 * len(item) - 1)
            for key, child in item.items():
                if type(key) is not str:
                    _fail(code)
                stack.append((key, depth + 1)); stack.append((child, depth + 1))
        elif kind is list:
            if nodes + len(stack) + len(item) > node_limit:
                _fail("fcc_case_limit_exceeded")
            size += 2 + max(0, len(item) - 1)
            stack.extend((child, depth + 1) for child in item)
        elif kind is str:
            if len(item) > string_limit:
                _fail("fcc_case_limit_exceeded")
            try:
                size += len(_encoded(item))
            except (UnicodeError, ValueError):
                _fail(code)
        elif kind in (int, float, bool) or item is None:
            if kind is float and not math.isfinite(item):
                _fail(code)
            try:
                size += len(_encoded(item))
            except (ValueError, OverflowError):
                _fail(code)
        else:
            _fail(code)
        if size > byte_limit:
            _fail("fcc_case_limit_exceeded")
    raw = _encoded(value)
    if len(raw) > byte_limit:
        _fail("fcc_case_limit_exceeded")
    return json.loads(raw) if detach else value


def _keys(value, keys, code="fcc_case_invalid_packet"):
    if type(value) is not dict or set(value) != set(keys):
        _fail(code)


def _text(value, limit, *, nullable=False, code="fcc_case_invalid_packet"):
    if nullable and value is None:
        return
    if type(value) is not str or not value.strip() or len(value) > limit:
        _fail(code)


def _id(value, *, nullable=False, code="fcc_case_invalid_packet"):
    if nullable and value is None:
        return
    if type(value) is not str or not _ID.fullmatch(value):
        _fail(code)


def _sha(value, code="fcc_case_invalid_packet"):
    if type(value) is not str or not _SHA.fullmatch(value):
        _fail(code)


def _integer(value, minimum=0, maximum=None, *, nullable=False, code="fcc_case_invalid_packet"):
    if nullable and value is None:
        return
    if type(value) is not int or value < minimum or maximum is not None and value > maximum:
        _fail(code)


def _choice(value, allowed, code="fcc_case_invalid_packet"):
    if type(value) is not str or value not in allowed:
        _fail(code)


def _list(value, limit, *, minimum=0, code="fcc_case_invalid_packet"):
    if type(value) is not list:
        _fail(code)
    if len(value) > limit:
        _fail("fcc_case_limit_exceeded")
    if len(value) < minimum:
        _fail(code)


def _strings(value, count, length, *, ids=False, minimum=0, code="fcc_case_invalid_packet"):
    _list(value, count, minimum=minimum, code=code)
    for item in value:
        _id(item, code=code) if ids else _text(item, length, code=code)
    if ids and len(set(value)) != len(value):
        _fail(code)


def _day(value):
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value, re.ASCII):
        _fail()
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail()


def _time(value):
    if type(value) is not str or not _TIMESTAMP.fullmatch(value):
        _fail()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        _fail()


def _url(value, *, nullable=False, official=False):
    if nullable and value is None:
        return
    _text(value, 4096)
    if any(ord(char) < 33 or ord(char) == 127 for char in value):
        _fail()
    parsed = urlsplit(value)
    try:
        parsed.port
    except ValueError:
        _fail()
    if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None
            or parsed.password is not None):
        _fail()
    if official and not (parsed.hostname.lower() == "fcc.gov" or parsed.hostname.lower().endswith(".fcc.gov")):
        _fail()


def _decode(raw, *, byte_limit=_PACKET_BYTES):
    if type(raw) not in (str, bytes):
        _fail()
    try:
        payload = raw.encode("utf-8") if type(raw) is str else raw
        if len(payload) > byte_limit:
            _fail("fcc_case_limit_exceeded")
        text = payload.decode("utf-8")
        def pairs(rows):
            result = {}
            for key, value in rows:
                if key in result:
                    _fail()
                result[key] = value
            return result
        def finite(text):
            value = float(text)
            if not math.isfinite(value):
                _fail()
            return value
        def constant(_):
            _fail()
        return json.loads(text, object_pairs_hook=pairs, parse_float=finite, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError, OverflowError) as error:
        if isinstance(error, FccReportCaseError):
            raise
        _fail()


def _normalize(value):
    return value.strip().casefold()


def _unique(values):
    result = {}
    for value in sorted(values):
        result.setdefault(_normalize(value), value.strip())
    return [result[key] for key in sorted(result)]


def _public_read_pdf(payload, filename, limits):
    """Read a public permission PDF once, without serializing derived PDF bytes.

    The caller gates this helper to an official/mirror exhibit. PdfReader's
    constructor performs the sole empty-password verification; its recorded
    USER_PASSWORD result is checked without a second decrypt/verify attempt.
    Missing or changed authentication internals fail closed.
    """
    try:
        import pypdf
        from pypdf._encryption import PasswordType
    except ImportError:
        _fail("fcc_case_extraction_unavailable")
    result = _extract._new_result(filename, hashlib.sha256(payload).hexdigest(), len(payload), limits)
    result["parser"] = {"name": "pypdf-public-empty-user-password", "version": pypdf.__version__}
    warnings = _extract._PdfWarnings()
    logger = logging.getLogger("pypdf")
    observable = _extract._warnings_observable()
    logger.addHandler(warnings)
    reader, stream = None, BytesIO(payload)
    try:
        try:
            reader = pypdf.PdfReader(stream, strict=True, password="")
            authentication = getattr(getattr(reader, "_encryption", None), "_password_type", None)
            if not reader.is_encrypted or authentication != PasswordType.USER_PASSWORD:
                _fail("fcc_case_pdf_invalid")
            result["total_pages"] = len(reader.pages)
        except Exception:
            _fail("fcc_case_pdf_invalid")
        _extract._issue(result, "public_empty_user_password_read")
        count = min(result["total_pages"], limits.max_pages)
        if count < result["total_pages"]:
            _extract._issue(result, "page_limit")
        remaining = limits.max_output_chars
        for index in range(count):
            number = index + 1
            if not remaining:
                _extract._issue(result, "output_limit", number)
                break
            warnings.page_number = number
            try:
                page = reader.pages[index]
                has_image, has_marks, missing_form_resources = _extract._inspect_content(
                    page.get_contents(), page.get("/Resources", {}), reader, limits.max_page_content_bytes)
                if missing_form_resources:
                    _extract._issue(result, "form_resources_missing", number)
                text = page.extract_text()
                if not isinstance(text, str):
                    raise ValueError("Unexpected PDF text result")
                truncated = len(text) > remaining
                status = ("truncated" if truncated else "ok" if text.strip() else
                          "image_only" if has_image else "no_text" if has_marks else "empty")
                result["pages"].append(_extract._page(number, text[:remaining], status))
                remaining -= min(len(text), remaining)
                if status in {"image_only", "no_text"}:
                    _extract._issue(result, "ocr_required" if status == "image_only" else "no_text", number)
                if truncated:
                    _extract._issue(result, "output_limit", number)
                    break
            except _extract._ContentLimit:
                result["pages"].append(_extract._page(number, "", "limit_exceeded"))
                _extract._issue(result, "content_limit", number)
            except Exception:
                result["pages"].append(_extract._page(number, "", "error"))
                _extract._issue(result, "page_error", number)
        _extract._status(result, _extract._pdf_status(result))
    finally:
        try:
            if reader is not None:
                reader.close()
        finally:
            stream.close()
            logger.removeHandler(warnings)
            warnings.close()
    for number in sorted(warnings.pages, key=lambda page: page or 0):
        _extract._issue(result, "parser_warning", number)
    observable = observable and _extract._warnings_observable()
    if not observable:
        _extract._issue(result, "parser_warnings_unobservable")
    if (warnings.pages or not observable) and result["status"] in {"ok", "empty"}:
        _extract._status(result, _extract._pdf_status(result))
    return result


def _page_scope(policy, documents):
    policy = _plain(policy, byte_limit=64 * 1024, depth_limit=6, node_limit=4096)
    _keys(policy, {"schema_version", "sources"})
    if type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        _fail()
    sources = policy["sources"]
    if type(sources) is dict and len(sources) > 16:
        _fail("fcc_case_limit_exceeded")
    if type(sources) is not dict or set(sources) != {document["sha256"] for document in documents}:
        _fail()
    total = 0
    for document in documents:
        entry = sources[document["sha256"]]
        _keys(entry, {"pages", "mode", "basis_id", "basis_sha256"})
        _list(entry["pages"], 200, minimum=1)
        for number in entry["pages"]:
            _integer(number, 1, document["physical_pages"])
        if len(set(entry["pages"])) != len(entry["pages"]):
            _fail()
        entry["pages"].sort()
        _choice(entry["mode"], {"native_text", "accessibility"})
        _id(entry["basis_id"]); _sha(entry["basis_sha256"])
        total += len(entry["pages"])
        if total > 800:
            _fail("fcc_case_limit_exceeded")
    return sources


def _selected_evidence(packet, scopes):
    for case in packet["cases"]:
        for claim in case["claims"]:
            for evidence in claim["evidence"]:
                if evidence["file_page"] not in scopes[evidence["source_sha256"]]["pages"]:
                    _fail("fcc_case_invalid_evidence")


def _strict_leaf_count(reader):
    """Validate every tree Count without opening any page content stream."""
    from pypdf.generic import ArrayObject, DictionaryObject

    root = reader.root_object["/Pages"].get_object()
    if not isinstance(root, DictionaryObject) or root.get("/Type") != "/Pages":
        _fail("fcc_case_pdf_invalid")
    counts, seen, stack = {}, set(), [(root, False)]
    while stack:
        node, exiting = stack.pop()
        identity = id(node)
        if exiting:
            actual = sum(counts[id(child.get_object())] for child in node["/Kids"])
            if node["/Count"] != actual:
                _fail("fcc_case_pdf_invalid")
            counts[identity] = actual
            continue
        if not isinstance(node, DictionaryObject) or identity in seen:
            _fail("fcc_case_pdf_invalid")
        seen.add(identity)
        if node.get("/Type") == "/Page" and "/Kids" not in node:
            counts[identity] = 1
        elif node.get("/Type") == "/Pages":
            kids, count = node.get("/Kids"), node.get("/Count")
            kids = kids.get_object() if kids is not None else None
            count = count.get_object() if count is not None else None
            if (not isinstance(kids, ArrayObject) or not isinstance(count, int)
                    or isinstance(count, bool) or count < 0):
                _fail("fcc_case_pdf_invalid")
            stack.append((node, True))
            stack.extend((child.get_object(), False) for child in reversed(kids))
        else:
            _fail("fcc_case_pdf_invalid")
    return counts[id(root)]


class _ScopedPdf:
    """An original-byte reader kept only between metadata preflight and reading."""

    def __init__(self, payload, document, scope):
        self.reader, self.stream = None, BytesIO(payload)
        self.warnings, self.observable = _extract._PdfWarnings(), _extract._warnings_observable()
        self.scope = scope
        logger = logging.getLogger("pypdf")
        logger.addHandler(self.warnings)
        try:
            try:
                import pypdf
                from pypdf._encryption import PasswordType
                from pypdf.constants import UserAccessPermissions
            except ImportError:
                _fail("fcc_case_extraction_unavailable")
            if not payload.startswith(b"%PDF-"):
                _fail("fcc_case_pdf_invalid")
            if not callable(getattr(pypdf.PdfReader, "_handle_encryption", None)):
                _fail("fcc_case_extraction_unavailable")

            class RejectEncryptedReader(pypdf.PdfReader):
                def _handle_encryption(self, password):
                    raise _extract._EncryptedPdf()

            try:
                self.reader = RejectEncryptedReader(self.stream, strict=True)
            except _extract._EncryptedPdf:
                self.stream.close()
                if not any(exhibit["source_kind"] in {"official", "mirror"} for exhibit in document["exhibits"]):
                    _fail("fcc_case_pdf_invalid")
                self.stream = BytesIO(payload)
                self.reader = pypdf.PdfReader(self.stream, strict=True, password="")
                encryption = getattr(self.reader, "_encryption", None)
                if not hasattr(encryption, "_password_type"):
                    _fail("fcc_case_extraction_unavailable")
                authentication = encryption._password_type
                if type(authentication) is not PasswordType:
                    _fail("fcc_case_extraction_unavailable")
                if not self.reader.is_encrypted or authentication != PasswordType.USER_PASSWORD:
                    _fail("fcc_case_pdf_invalid")
            if self.reader.is_encrypted:
                required = (UserAccessPermissions.EXTRACT if scope["mode"] == "native_text"
                            else UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS)
                try:
                    permissions = self.reader.user_access_permissions
                    integrity = self.reader.are_permissions_valid
                except Exception:
                    _fail("fcc_case_extraction_unavailable")
                if (integrity is not True or not isinstance(permissions, UserAccessPermissions)
                        or not permissions & required):
                    _fail("fcc_case_extraction_unavailable")
            if not callable(getattr(self.reader, "_flatten", None)):
                _fail("fcc_case_extraction_unavailable")
            actual = _strict_leaf_count(self.reader)
            self.reader._flatten()
            if not isinstance(getattr(self.reader, "flattened_pages", None), list):
                _fail("fcc_case_extraction_unavailable")
            if actual != document["physical_pages"] or len(self.reader.flattened_pages) != actual:
                _fail("fcc_case_pdf_invalid")
            if type(getattr(pypdf, "__version__", None)) is not str:
                _fail("fcc_case_extraction_unavailable")
            self.total_pages, self.version = actual, pypdf.__version__
        except Exception as error:
            self.close()
            if isinstance(error, FccReportCaseError):
                raise
            _fail("fcc_case_pdf_invalid")
        finally:
            logger.removeHandler(self.warnings)
            self.observable = self.observable and _extract._warnings_observable()

    def close(self):
        try:
            if self.reader is not None:
                self.reader.close()
        finally:
            self.stream.close()
            self.warnings.close()

    def read(self, document, limits):
        result = _extract._new_result(document["document_id"] + ".pdf", document["sha256"], document["size_bytes"], limits)
        encrypted = self.reader.is_encrypted
        parser = ("pypdf-public-empty-user-password-accessibility-selected-pages" if self.scope["mode"] == "accessibility"
                  else "pypdf-public-empty-user-password-selected-pages") if encrypted else "pypdf-selected-pages"
        result["parser"] = {"name": parser, "version": self.version}
        result["total_pages"] = self.total_pages
        for code in ("page_scope_applied", "page_scope_" + self.scope["mode"]):
            _extract._issue(result, code)
        if encrypted:
            _extract._issue(result, "public_empty_user_password_read")
        for number in self.scope["pages"]:
            _extract._issue(result, "page_scope_requested", number)
        partial = len(self.scope["pages"]) < self.total_pages
        if partial:
            _extract._issue(result, "page_scope_outside_unprocessed")
        remaining = limits.max_output_chars
        logger = logging.getLogger("pypdf")
        logger.addHandler(self.warnings)
        try:
            for number in self.scope["pages"]:
                if not remaining:
                    _extract._issue(result, "output_limit", number)
                    break
                self.warnings.page_number = number
                try:
                    page = self.reader.flattened_pages[number - 1]
                    has_image, has_marks, missing_form_resources = _extract._inspect_content(
                        page.get_contents(), page.get("/Resources", {}), self.reader, limits.max_page_content_bytes)
                    if missing_form_resources:
                        _extract._issue(result, "form_resources_missing", number)
                    text = page.extract_text()
                    if not isinstance(text, str):
                        raise ValueError("Unexpected PDF text result")
                    truncated = len(text) > remaining
                    status = ("truncated" if truncated else "ok" if text.strip() else
                              "image_only" if has_image else "no_text" if has_marks else "empty")
                    result["pages"].append(_extract._page(number, text[:remaining], status))
                    remaining -= min(len(text), remaining)
                    if status in {"image_only", "no_text"}:
                        _extract._issue(result, "ocr_required" if status == "image_only" else "no_text", number)
                    if truncated:
                        _extract._issue(result, "output_limit", number)
                        break
                except _extract._ContentLimit:
                    result["pages"].append(_extract._page(number, "", "limit_exceeded"))
                    _extract._issue(result, "content_limit", number)
                except Exception:
                    result["pages"].append(_extract._page(number, "", "error"))
                    _extract._issue(result, "page_error", number)
        finally:
            logger.removeHandler(self.warnings)
        for number in sorted(self.warnings.pages, key=lambda page: page or 0):
            _extract._issue(result, "parser_warning", number)
        if not self.observable or not _extract._warnings_observable():
            _extract._issue(result, "parser_warnings_unobservable")
        return _extract._status(result, "partial" if partial else _extract._pdf_status(result))


class _PacketMetadata:
    """Shared packet structure only; never opens or qualifies a source PDF."""

    def __init__(self, packet):
        packet = _plain(packet)
        _keys(packet, {"schema_version", "corpus_id", "scope", "searches", "documents", "cases"})
        if type(packet["schema_version"]) is not int or packet["schema_version"] != 1:
            _fail()
        _id(packet["corpus_id"])
        self._packet = packet
        self._validate_scope_searches()
        self._validate_documents()
        self._validate_cases()

    def _validate_scope_searches(self):
        scope = self._packet["scope"]
        _keys(scope, {"issue_date_from", "cutoff_at", "timezone", "population_status",
                      "search_scope_notes", "unverified_ranges", "synthetic"})
        if (scope["issue_date_from"] != "2025-01-01" or scope["timezone"] != "Asia/Seoul"
                or scope["population_status"] != "unconfirmed" or type(scope["synthetic"]) is not bool):
            _fail()
        self._cutoff = _time(scope["cutoff_at"])
        if self._cutoff.date() < _day(scope["issue_date_from"]):
            _fail()
        _strings(scope["search_scope_notes"], 32, 2048)
        _strings(scope["unverified_ranges"], 32, 2048)
        _list(self._packet["searches"], 128)
        self._search_ids = set()
        for search in self._packet["searches"]:
            _keys(search, {"search_id", "institution_scope", "query", "url", "searched_at", "status",
                           "page_start", "page_end", "result_limit", "candidate_count", "unverified_ranges", "notes"})
            _id(search["search_id"])
            if search["search_id"] in self._search_ids:
                _fail()
            self._search_ids.add(search["search_id"])
            _choice(search["institution_scope"], {"hct_korea", "hct_america", "mixed", "unresolved"})
            _text(search["query"], 4096); _url(search["url"])
            _choice(search["status"], {"ok", "partial", "blocked", "failed"})
            if _time(search["searched_at"]) > self._cutoff:
                _fail()
            for key in ("page_start", "page_end", "result_limit"):
                _integer(search[key], 1, nullable=True)
            _integer(search["candidate_count"], nullable=True)
            if ((search["page_start"] is None) != (search["page_end"] is None)
                    or search["page_start"] is not None and search["page_start"] > search["page_end"]):
                _fail()
            _strings(search["unverified_ranges"], 32, 2048)
            _text(search["notes"], 2048, nullable=True)

    def _validate_documents(self):
        _list(self._packet["documents"], 16)
        self._document_rows, hashes, exhibits = {}, set(), 0
        for document in self._packet["documents"]:
            _keys(document, {"document_id", "sha256", "size_bytes", "physical_pages", "exhibits", "rights"})
            _id(document["document_id"]); _sha(document["sha256"])
            if document["document_id"] in self._document_rows or document["sha256"] in hashes:
                _fail()
            self._document_rows[document["document_id"]] = document
            hashes.add(document["sha256"])
            _integer(document["size_bytes"], 1)
            if document["size_bytes"] > _PDF_BYTES:
                _fail("fcc_case_limit_exceeded")
            _integer(document["physical_pages"], 1, 100000)
            _keys(document["rights"], {"status", "notes", "public_redistribution_allowed", "external_model_use_allowed"})
            _choice(document["rights"]["status"], {"private_only", "permission_recorded", "unresolved"})
            _text(document["rights"]["notes"], 2048, nullable=True)
            if (document["rights"]["public_redistribution_allowed"] is not False
                    or document["rights"]["external_model_use_allowed"] is not False):
                _fail()
            _list(document["exhibits"], 64, minimum=1)
            exhibits += len(document["exhibits"])
            if exhibits > 256:
                _fail("fcc_case_limit_exceeded")
            seen = set()
            for exhibit in document["exhibits"]:
                _keys(exhibit, {"exhibit_id", "fcc_id", "application_id", "exhibit_type", "url", "source_kind",
                                "accessed_at", "official_match_status", "official_url", "search_ids"})
                _text(exhibit["exhibit_id"], 128)
                for key, limit in (("fcc_id", 128), ("application_id", 256), ("exhibit_type", 256)):
                    _text(exhibit[key], limit, nullable=True)
                _choice(exhibit["source_kind"], {"official", "mirror", "existing_user"})
                _url(exhibit["url"], nullable=exhibit["source_kind"] == "existing_user",
                     official=exhibit["source_kind"] == "official")
                _time(exhibit["accessed_at"])
                _choice(exhibit["official_match_status"], {"unverified", "listing_only", "pdf_hash_matched", "blocked"})
                required = exhibit["official_match_status"] in {"listing_only", "pdf_hash_matched"}
                _url(exhibit["official_url"], nullable=not required, official=True)
                if exhibit["source_kind"] == "official" and exhibit["official_url"] is None:
                    _fail()
                _strings(exhibit["search_ids"], 32, 128, ids=True)
                if not set(exhibit["search_ids"]) <= self._search_ids:
                    _fail()
                key = (exhibit["exhibit_id"], exhibit["url"])
                if key in seen:
                    _fail()
                seen.add(key)

    def _validate_cases(self):
        _list(self._packet["cases"], 128)
        ids, claims, evidence_count = set(), 0, 0
        for case in self._packet["cases"]:
            _keys(case, {"case_id", "report_group_id", "document_ids", "claims", "relations", "reuse_group_ids"})
            _id(case["case_id"]); _id(case["report_group_id"], nullable=True)
            if case["case_id"] in ids:
                _fail()
            ids.add(case["case_id"])
            _strings(case["document_ids"], 16, 128, ids=True, minimum=1)
            if not set(case["document_ids"]) <= set(self._document_rows):
                _fail()
            _strings(case["reuse_group_ids"], 32, 128, ids=True)
            _list(case["claims"], 64)
            claims += len(case["claims"])
            if claims > 1024:
                _fail("fcc_case_limit_exceeded")
            seen = set()
            for claim in case["claims"]:
                _keys(claim, {"claim_id", "field", "value", "unit", "status", "basis", "evidence"})
                _id(claim["claim_id"])
                if claim["claim_id"] in seen:
                    _fail()
                seen.add(claim["claim_id"])
                _text(claim["field"], 128)
                if not _FIELD.fullmatch(claim["field"]):
                    _fail()
                _plain(claim["value"], depth_limit=6, detach=False)
                _text(claim["unit"], 64, nullable=True)
                _choice(claim["status"], _STATUSES); _choice(claim["basis"], _BASES)
                _list(claim["evidence"], 8)
                evidence_count += len(claim["evidence"])
                if evidence_count > 4096:
                    _fail("fcc_case_limit_exceeded")
                value = claim["value"]
                if claim["status"] in {"not_reported", "extraction_failed"}:
                    if value is not None or claim["evidence"]:
                        _fail()
                if claim["status"] in {"reviewed", "extracted"}:
                    if (value is None or type(value) is str and not value.strip()
                            or type(value) in (list, dict) and not value or not claim["evidence"]):
                        _fail()
                for evidence in claim["evidence"]:
                    self._validate_evidence_metadata(case, evidence)
            _list(case["relations"], 32)
        for case in self._packet["cases"]:
            seen = set()
            for relation in case["relations"]:
                _keys(relation, {"relation_id", "kind", "target_case_id", "external_target", "status"})
                _id(relation["relation_id"])
                if relation["relation_id"] in seen:
                    _fail()
                seen.add(relation["relation_id"])
                _choice(relation["kind"], {"revision_of", "part_of", "appendix_of", "exhibit_of"})
                _choice(relation["status"], {"resolved", "unresolved"})
                if relation["status"] == "resolved":
                    _id(relation["target_case_id"])
                    if (relation["target_case_id"] not in ids or relation["target_case_id"] == case["case_id"]
                            or relation["external_target"] is not None):
                        _fail()
                elif relation["target_case_id"] is not None:
                    _fail()
                else:
                    _text(relation["external_target"], 256)

    def _validate_evidence_metadata(self, case, evidence):
        code = "fcc_case_invalid_evidence"
        _keys(evidence, _EVIDENCE, code)
        _id(evidence["document_id"], code=code); _sha(evidence["source_sha256"], code)
        _sha(evidence["text_sha256"], code)
        if evidence["document_id"] not in case["document_ids"]:
            _fail(code)
        document = self._document_rows[evidence["document_id"]]
        if evidence["source_sha256"] != document["sha256"]:
            _fail(code)
        for key in ("file_page", "line_start", "line_end"):
            _integer(evidence[key], 1, code=code)
        if evidence["file_page"] > document["physical_pages"]:
            _fail(code)
        if evidence["line_end"] < evidence["line_start"] or evidence["line_end"] - evidence["line_start"] >= 40:
            _fail(code)
        for key in ("printed_page", "table", "row", "column"):
            _text(evidence[key], 128, nullable=True, code=code)
        _strings(evidence["footnotes"], 16, 512, code=code)
        _text(evidence["quote"], 8192, code=code)


def _preparation_path(value, *, json_only=False):
    _text(value, 16384)
    try:
        _manifest_path(value)
    except ControlPacketAuditError:
        _fail()
    if json_only and not value.lower().endswith(".json"):
        _fail()
    return value


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@_public("fcc_case_invalid_packet")
def prepare_fcc_case_packet(manifest_json, json_files, *, expected_manifest_sha256, packet_path, page_scope_path):
    """Bind two pinned metadata inputs; no source bytes or literals are verified."""
    _sha(expected_manifest_sha256)
    if type(manifest_json) is not bytes:
        _fail()
    if len(manifest_json) > _MIB:
        _fail("fcc_case_limit_exceeded")
    if hashlib.sha256(manifest_json).hexdigest() != expected_manifest_sha256:
        _fail("fcc_case_invalid_sources")
    manifest = _plain(_decode(manifest_json, byte_limit=_MIB), byte_limit=_MIB)
    if type(manifest) is not dict or not {"request_id", "revision", "files"} <= set(manifest):
        _fail()
    if manifest["request_id"] != "DEV-HCT-FCC-CORPUS-012":
        _fail()
    _id(manifest["revision"])
    for flag in ("source_code_executed", "runtime_or_hardware_support_confirmed", "public_export_allowed"):
        if flag in manifest and manifest[flag] is not False:
            _fail()
    _list(manifest["files"], 128, minimum=2)
    rows, seen = {}, set()
    for row in manifest["files"]:
        _keys(row, {"path", "bytes", "sha256"})
        path = _preparation_path(row["path"])
        _integer(row["bytes"]); _sha(row["sha256"])
        if path.casefold() in seen:
            _fail()
        seen.add(path.casefold()); rows[path] = row
    packet_path = _preparation_path(packet_path, json_only=True)
    page_scope_path = _preparation_path(page_scope_path, json_only=True)
    if packet_path.casefold() == page_scope_path.casefold():
        _fail()
    selected = {packet_path, page_scope_path}
    if (type(json_files) is not dict or len(json_files) != 2
            or any(type(path) is not str for path in json_files)):
        _fail("fcc_case_invalid_sources")
    if set(json_files) != selected or not selected <= set(rows):
        _fail("fcc_case_invalid_sources")
    total = 0
    for path, limit in ((packet_path, _PACKET_BYTES), (page_scope_path, 64 * 1024)):
        raw = json_files[path]
        if type(raw) is not bytes:
            _fail("fcc_case_invalid_sources")
        total += len(raw)
        if rows[path]["bytes"] > limit or len(raw) > limit or total > _PACKET_BYTES + 64 * 1024:
            _fail("fcc_case_limit_exceeded")
        if len(raw) != rows[path]["bytes"] or hashlib.sha256(raw).hexdigest() != rows[path]["sha256"]:
            _fail("fcc_case_invalid_sources")
    validated = _PacketMetadata(_decode(json_files[packet_path]))
    packet = validated._packet
    if sum(document["size_bytes"] for document in packet["documents"]) > _PDF_TOTAL:
        _fail("fcc_case_limit_exceeded")
    scopes = _page_scope(_decode(json_files[page_scope_path], byte_limit=64 * 1024), packet["documents"])
    _selected_evidence(packet, scopes)
    policy = {"schema_version": 1, "sources": scopes}
    result = {"schema_version": 1, "kind": "fcc_case_packet_preparation", "packet": packet, "page_scope": policy,
              "source_refs": [{key: document[key] for key in ("document_id", "sha256", "size_bytes", "physical_pages")}
                              for document in sorted(packet["documents"], key=lambda row: row["document_id"])],
              "provenance": {"manifest_sha256": expected_manifest_sha256,
                             "consumed_files": [rows[path] for path in sorted(selected)],
                             "packet_sha256": hashlib.sha256(_canonical(packet)).hexdigest(),
                             "page_scope_sha256": hashlib.sha256(_canonical(policy)).hexdigest()},
              "verification": {"manifest_and_consumed_json_bytes_verified": True,
                               "source_pdf_bytes_verified": False, "retained_literals_verified": False,
                               "authority_or_rights_verified": False, "execution_authorized": False}}
    encoded = _canonical(result)
    if len(encoded) > _OUTPUT_BYTES:
        _fail("fcc_case_limit_exceeded")
    return json.loads(encoded)


class FccReportCaseCatalog(_PacketMetadata):
    @_public("fcc_case_invalid_packet")
    def __init__(self, packet, pdf_sources, *, page_scope=None):
        super().__init__(packet)
        packet = self._packet
        blobs = self._sources(pdf_sources)
        self._extractions, self._documents = {}, {}
        if page_scope is not None:
            scopes = _page_scope(page_scope, packet["documents"])
            _selected_evidence(packet, scopes)
            self._read_scoped(blobs, scopes)
        remaining_pages, remaining_chars = 800, 4000000
        for document in packet["documents"] if page_scope is None else ():
            if remaining_pages <= 0 or remaining_chars <= 0:
                _fail("fcc_case_limit_exceeded")
            payload = blobs[document["sha256"]]
            if not payload.startswith(b"%PDF-"):
                _fail("fcc_case_pdf_invalid")
            limits = ExtractionLimits(max_input_bytes=_PDF_BYTES, max_pages=min(200, remaining_pages),
                                      max_output_chars=min(1000000, remaining_chars),
                                      max_page_content_bytes=8 * _MIB)
            result = extract_document(payload, document["document_id"] + ".pdf", limits=limits)
            if result["status"] == "encrypted" and any(exhibit["source_kind"] in {"official", "mirror"}
                                                        for exhibit in document["exhibits"]):
                result = _public_read_pdf(payload, document["document_id"] + ".pdf", limits)
            if result["status"] == "parser_unavailable":
                _fail("fcc_case_extraction_unavailable")
            if (result["status"] not in {"ok", "empty", "partial", "image_only", "no_text", "limit_exceeded", "parser_error"}
                    or type(result["total_pages"]) is not int or result["total_pages"] < 1
                    or result["total_pages"] != document["physical_pages"]
                    or result["source"]["sha256"] != document["sha256"]
                    or result["source"]["size_bytes"] != document["size_bytes"]):
                _fail("fcc_case_pdf_invalid")
            remaining_pages -= result["processed_pages"]
            remaining_chars -= sum(len(page["text"]) for page in result["pages"])
            if remaining_pages < 0 or remaining_chars < 0:
                _fail("fcc_case_limit_exceeded")
            self._extractions[document["document_id"]] = result
            self._documents[document["document_id"]] = self._document_dto(document, result)
        self._cases = {case["case_id"]: case for case in packet["cases"]}
        self._previews = {}
        for case in packet["cases"]:
            for claim in case["claims"]:
                for evidence in claim["evidence"]:
                    self._validate_evidence(case, evidence)
                    evidence["literal_verified"] = True
            self._previews[case["case_id"]] = self._preview(case)
        self._summary = self._build_summary()

    @classmethod
    @_public("fcc_case_invalid_packet")
    def from_json(cls, packet_json, pdf_sources, *, page_scope=None):
        return cls(_decode(packet_json), pdf_sources, page_scope=page_scope)

    def _read_scoped(self, blobs, scopes):
        readers = []
        try:
            # Every source must pass metadata, leaf-count and permission checks
            # before the first selected page's content stream can be opened.
            for document in self._packet["documents"]:
                readers.append(_ScopedPdf(blobs[document["sha256"]], document, scopes[document["sha256"]]))
            remaining_chars = 4000000
            for document, reader in zip(self._packet["documents"], readers):
                if remaining_chars <= 0:
                    _fail("fcc_case_limit_exceeded")
                limits = ExtractionLimits(max_input_bytes=_PDF_BYTES, max_pages=200,
                                          max_output_chars=min(1000000, remaining_chars), max_page_content_bytes=8 * _MIB)
                result = reader.read(document, limits)
                remaining_chars -= sum(len(page["text"]) for page in result["pages"])
                self._extractions[document["document_id"]] = result
                self._documents[document["document_id"]] = self._document_dto(document, result)
        finally:
            for reader in readers:
                reader.close()

    def _sources(self, supplied):
        if type(supplied) is not dict:
            _fail("fcc_case_invalid_sources")
        if len(supplied) > 16:
            _fail("fcc_case_limit_exceeded")
        total = 0
        for key, value in supplied.items():
            _sha(key, "fcc_case_invalid_sources")
            if type(value) is not bytes:
                _fail("fcc_case_invalid_sources")
            total += len(value)
            if len(value) > _PDF_BYTES or total > _PDF_TOTAL:
                _fail("fcc_case_limit_exceeded")
        if set(supplied) != {document["sha256"] for document in self._packet["documents"]}:
            _fail("fcc_case_invalid_sources")
        for document in self._packet["documents"]:
            blob = supplied[document["sha256"]]
            if len(blob) != document["size_bytes"] or hashlib.sha256(blob).hexdigest() != document["sha256"]:
                _fail("fcc_case_invalid_sources")
        return dict(supplied)

    @staticmethod
    def _citable(result, page):
        if result["status"] not in {"ok", "partial"} or page["status"] != "ok" or not page["text"].strip():
            return False
        blocked = {"parser_warning", "parser_warnings_unobservable", "form_resources_missing", "page_error", "content_limit"}
        return not any(issue["code"] in blocked and issue.get("page_number") in (None, page["page_number"])
                       for issue in result["issues"])

    def _document_dto(self, document, result):
        return {**document, "extraction": {
            "status": result["status"], "complete": result["complete"], "total_pages": result["total_pages"],
            "processed_pages": result["processed_pages"], "parser": result["parser"],
            "issues": [{"code": issue["code"], "file_page": issue.get("page_number")} for issue in result["issues"]]},
            "page_index": [{"file_page": page["page_number"], "status": page["status"],
                            "text_sha256": page["text_sha256"], "line_count": len(page["line_spans"]),
                            "citable": self._citable(result, page)} for page in result["pages"]]}

    def _validate_evidence(self, case, evidence):
        code = "fcc_case_invalid_evidence"
        result = self._extractions[evidence["document_id"]]
        if evidence["source_sha256"] != result["source"]["sha256"]:
            _fail(code)
        pages = [page for page in result["pages"] if page["page_number"] == evidence["file_page"]]
        if len(pages) != 1 or not self._citable(result, pages[0]):
            _fail(code)
        try:
            citation = page_citation(result, evidence["file_page"], evidence["line_start"], evidence["line_end"])
        except Exception:
            _fail(code)
        if citation["text_sha256"] != evidence["text_sha256"] or citation["quote"] != evidence["quote"]:
            _fail(code)

    @staticmethod
    def _values(case, field, *, bases=("report_fact",), scalar_only=False):
        values = []
        for claim in case["claims"]:
            if claim["field"] != field or claim["status"] != "reviewed" or claim["basis"] not in bases:
                continue
            value = claim["value"]
            if type(value) is str and value.strip():
                values.append(value)
            elif not scalar_only and type(value) is list and all(type(item) is str and item.strip() for item in value):
                values.extend(value)
        return _unique(values)

    def _preview(self, case):
        conflict = any(claim["status"] == "conflicting" for claim in case["claims"])
        def scalar(field, bases=("report_fact",)):
            nonlocal conflict
            if any(claim["field"] == field and claim["basis"] in bases
                   and claim["status"] in {"ambiguous", "conflicting"} for claim in case["claims"]):
                return None
            values = self._values(case, field, bases=bases, scalar_only=True)
            if len(values) > 1:
                conflict = True
            return values[0] if len(values) == 1 else None
        number, revision = scalar("report.number"), scalar("report.revision")
        issued = scalar("report.issue_date")
        if issued is None:
            scope = "pending"
        else:
            issued_day = _day(issued)
            scope = ("out_of_range" if issued_day < date(2025, 1, 1) else
                     "future" if issued_day > self._cutoff.date() else "in_scope")
        legal, address = scalar("issuer.legal_name"), scalar("issuer.address")
        classification = scalar("issuer.classification", ("report_fact", "developer_inference"))
        issuer = classification if legal and address and classification in {"hct_korea", "hct_america"} else "unknown"
        family, manufacturer = scalar("product.family"), scalar("product.manufacturer")
        preview = {"case_id": case["case_id"], "report_group_id": case["report_group_id"],
                   "report_number": number, "revision": revision, "issuer_class": issuer, "issue_date": issued,
                   "scope_status": scope, "fcc_ids": self._values(case, "report.fcc_ids"),
                   "product_family": family, "manufacturer": manufacturer,
                   "models": self._values(case, "product.models"), "rules": self._values(case, "method.rules"),
                   "methods": self._values(case, "method.references", bases=("report_fact", "standard_reference_only")),
                   "equipment_models": self._values(case, "equipment.models"),
                   "review_status": "conflicting" if conflict else
                       "reviewed" if case["claims"] and all(c["status"] == "reviewed" for c in case["claims"]) else
                       "partial" if any(c["status"] == "reviewed" for c in case["claims"]) else "unreviewed",
                   "document_ids": list(case["document_ids"]), "evaluation_group": None}
        missing = []
        for name, known in (("product_family", family), ("fcc_ids", preview["fcc_ids"]),
                            ("report_group_id", case["report_group_id"]), ("reuse_group_ids", case["reuse_group_ids"]),
                            ("issuer_class", issuer != "unknown"), ("scope_status", scope == "in_scope"),
                            ("review_status", preview["review_status"] == "reviewed")):
            if not known:
                missing.append(name)
        keys = (["family:" + _normalize(family)] if family else [])
        keys += ["fcc:" + _normalize(value) for value in preview["fcc_ids"]]
        keys += ["source:" + self._document_rows[identifier]["sha256"] for identifier in case["document_ids"]]
        if case["report_group_id"]:
            keys.append("report:" + case["report_group_id"])
        keys += ["reuse:" + value for value in case["reuse_group_ids"]]
        preview["evaluation_group"] = {"eligible": not missing, "keys": sorted(set(keys)), "missing": sorted(missing)}
        return preview

    def _wrapper(self, kind, **body):
        return {"schema_version": 1, "kind": kind, "corpus_id": self._packet["corpus_id"],
                "execution_mode": "report_derived", "synthetic": self._packet["scope"]["synthetic"],
                "validation_scope": "source_bytes_and_retained_page_literals_only",
                "verification": {"hardware_verified": False, "physical_verified": False,
                                 "model_execution_verified": False, "normative_compliance_verified": False,
                                 "coverage_complete": False}, **body}

    def _build_summary(self):
        documents = [self._documents[key] for key in sorted(self._documents)]
        previews = [self._previews[key] for key in sorted(self._previews)]
        claims = [claim for case in self._cases.values() for claim in case["claims"]]
        counts = {"candidate_count": None, "acquired_unique_pdfs": len(documents), "parsed_unique_pdfs": len(documents),
                  "complete_text_pdfs": sum(doc["extraction"]["status"] == "ok" for doc in documents),
                  "partial_text_pdfs": sum(doc["extraction"]["status"] == "partial" for doc in documents),
                  "no_citable_text_pdfs": sum(not any(page["citable"] for page in doc["page_index"]) for doc in documents),
                  "exhibit_relations": sum(len(doc["exhibits"]) for doc in documents), "case_count": len(previews),
                  "reviewed_claim_count": sum(claim["status"] == "reviewed" for claim in claims),
                  "gap_or_unreviewed_claim_count": sum(claim["status"] != "reviewed" for claim in claims),
                  "scope_counts": {state: sum(preview["scope_status"] == state for preview in previews)
                                   for state in ("in_scope", "pending", "out_of_range", "future")},
                  "independent_group_eligible_cases": sum(preview["evaluation_group"]["eligible"] for preview in previews),
                  "normative_comparison_completed_cases": None, "development_integrated_cases": None,
                  "model_evaluated_cases": 0}
        return self._wrapper("fcc_report_case_summary", scope=self._packet["scope"], searches=self._packet["searches"],
                             counts=counts, documents=documents, case_previews=previews)

    @staticmethod
    def _response(value):
        raw = _encoded(value)
        if len(raw) > _OUTPUT_BYTES:
            _fail("fcc_case_limit_exceeded")
        return json.loads(raw)

    @_public("fcc_case_invalid_query")
    def summary(self):
        return self._response(self._summary)

    @_public("fcc_case_invalid_query")
    def case(self, case_id):
        _id(case_id, code="fcc_case_invalid_query")
        if case_id not in self._cases:
            _fail("fcc_case_not_found")
        case = self._cases[case_id]
        return self._response(self._wrapper("fcc_report_case", case={**case, "preview": self._previews[case_id]},
                                           documents=[self._documents[key] for key in case["document_ids"]]))

    @staticmethod
    def _query(query):
        code = "fcc_case_invalid_query"
        query = _plain(query, code=code)
        _keys(query, {"product_family", "rule", "method", "model"}, code)
        for key, value in query.items():
            _text(value, 256, nullable=True, code=code)
            if value is not None:
                query[key] = value.strip()
        return query

    def _matches(self, query, *, binding=None, reasons=()):
        reasons = set(reasons)
        if any(query[key] is None for key in ("product_family", "rule", "method")):
            reasons.add("query_context_missing")
        matches = []
        model = query["model"] if query["model"] is not None else binding["model"] if binding else None
        if not reasons:
            for preview in self._previews.values():
                if (preview["issuer_class"] == "unknown" or preview["scope_status"] != "in_scope"
                        or preview["review_status"] == "conflicting" or preview["product_family"] is None):
                    continue
                if (_normalize(query["product_family"]) != _normalize(preview["product_family"])
                        or _normalize(query["rule"]) not in {_normalize(value) for value in preview["rules"]}
                        or _normalize(query["method"]) not in {_normalize(value) for value in preview["methods"]}):
                    continue
                relation = ("unspecified" if model is None else "exact_model" if
                            _normalize(model) in {_normalize(value) for value in preview["models"]} else "related_family")
                matches.append({"preview": preview, "model_relation": relation})
        if reasons:
            status = "insufficient_evidence"
        elif not matches:
            status = "no_match"; reasons.add("no_reviewed_case")
        elif model is not None and not any(item["model_relation"] == "exact_model" for item in matches):
            status = "insufficient_evidence"; reasons.add("exact_model_case_missing")
        else:
            status = "candidates"
        matches.sort(key=lambda item: (item["model_relation"] != "exact_model", item["preview"]["case_id"]))
        return self._response(self._wrapper("fcc_report_case_matches", query=query, status=status,
                                           reason_codes=sorted(reasons), intake_binding=binding, matches=matches))

    @_public("fcc_case_invalid_query")
    def search(self, query):
        return self._matches(self._query(query))

    @staticmethod
    def _discovery_text_values(claim, *, scalar=False):
        value = claim["value"]
        if type(value) is str and value.strip():
            return [value]
        if not scalar and type(value) is list and all(type(item) is str and item.strip() for item in value):
            return value
        return []

    def _discovery_criterion(self, case, name, query):
        field, bases = {
            "product_family": ("product.family", ("report_fact",)),
            "rule": ("method.rules", ("report_fact",)),
            "method": ("method.references", ("report_fact", "standard_reference_only")),
            "model": ("product.models", ("report_fact",)),
        }[name]
        claims = sorted((claim for claim in case["claims"] if claim["field"] == field),
                        key=lambda claim: claim["claim_id"])
        eligible, projections = [], []
        positions = ("document_id", "source_sha256", "file_page", "text_sha256", "line_start", "line_end")
        for claim in claims:
            values = self._discovery_text_values(claim, scalar=name == "product_family")
            if claim["status"] == "reviewed" and claim["basis"] in bases and values:
                eligible.append((claim["claim_id"], values))
            refs = [{key: evidence[key] for key in (*positions, "literal_verified")}
                    for evidence in claim["evidence"]]
            refs.sort(key=lambda ref: tuple(ref[key] for key in positions))
            projections.append({"claim_id": claim["claim_id"], "status": claim["status"], "basis": claim["basis"],
                                "value": claim["value"], "unit": claim["unit"], "evidence_refs": refs})
        values = _unique([value for _, members in eligible for value in members])
        if len(values) > 128:
            _fail("fcc_case_limit_exceeded")
        matched = [identifier for identifier, members in eligible
                   if query is not None and _normalize(query) in {_normalize(value) for value in members}]
        if query is None:
            status = "not_requested"
        elif (any(claim["status"] == "conflicting" for claim in claims)
                or name == "product_family" and len(values) > 1):
            status = "conflicting"
        elif any(claim["status"] == "ambiguous" for claim in claims):
            status = "unconfirmed"
        elif matched:
            status = "matched"
        elif not values or len(eligible) != len(claims):
            status = "unconfirmed"
        else:
            status = "mismatched"
        return {"query": query, "status": status, "reviewed_values": values,
                "matched_claim_ids": matched, "claims": projections}

    @staticmethod
    def _discovery_search_gate(preview, query):
        reasons = set()
        if any(query[key] is None for key in ("product_family", "rule", "method")):
            reasons.add("query_context_missing")
        if preview["issuer_class"] == "unknown":
            reasons.add("issuer_unconfirmed")
        if preview["scope_status"] != "in_scope":
            reasons.add("scope_" + preview["scope_status"])
        if preview["review_status"] == "conflicting":
            reasons.add("case_conflicting")
        for key, values in (("product_family", [preview["product_family"]] if preview["product_family"] else []),
                            ("rule", preview["rules"]), ("method", preview["methods"]), ("model", preview["models"])):
            if query[key] is None:
                continue
            if not values:
                reasons.add(key + "_unconfirmed")
            elif _normalize(query[key]) not in {_normalize(value) for value in values}:
                reasons.add(key + "_mismatch")
        return {"eligible": not reasons, "reason_codes": sorted(reasons)}

    def _discovery_issues(self, case, preview):
        issues = set()
        review = {"conflicting": "case_conflicting", "partial": "partial_review", "unreviewed": "unreviewed_case"}
        if preview["review_status"] in review:
            issues.add(review[preview["review_status"]])
        if preview["issuer_class"] == "unknown":
            issues.add("issuer_unconfirmed")
        if preview["scope_status"] != "in_scope":
            issues.add("scope_" + preview["scope_status"])
        if set(preview["evaluation_group"]["missing"]) & {"product_family", "fcc_ids", "report_group_id", "reuse_group_ids"}:
            issues.add("group_unconfirmed")
        for identifier in case["document_ids"]:
            document = self._documents[identifier]
            if document["extraction"]["status"] == "partial":
                issues.add("source_partial")
            if not any(page["citable"] for page in document["page_index"]):
                issues.add("source_without_citable_pages")
            if (not document["rights"]["public_redistribution_allowed"]
                    or not document["rights"]["external_model_use_allowed"]):
                issues.add("rights_restricted")
            if any(exhibit["official_match_status"] != "pdf_hash_matched" for exhibit in document["exhibits"]):
                issues.add("official_mapping_unverified")
        return sorted(issues)

    @_public("fcc_case_invalid_query")
    def discover(self, query):
        """Find material for review without granting execution or changing search."""
        query = self._query(query)
        if all(value is None for value in query.values()):
            return self._response(self._wrapper("fcc_report_case_discovery", query=query,
                status="insufficient_context", reason_codes=["discovery_context_missing"], items=[]))
        items = []
        for case in self._cases.values():
            criteria = {key: self._discovery_criterion(case, key, query[key])
                        for key in ("product_family", "rule", "method", "model")}
            if any(criteria[key]["status"] == "mismatched" for key in ("product_family", "rule", "method")):
                continue
            model_mismatch = criteria["model"]["status"] == "mismatched"
            if model_mismatch and not all(criteria[key]["status"] == "matched"
                                          for key in ("product_family", "rule", "method")):
                continue
            requested = [criterion["status"] for criterion in criteria.values() if criterion["query"] is not None]
            relation = ("conflicting" if "conflicting" in requested else
                        "unconfirmed" if "unconfirmed" in requested else
                        "related_model" if model_mismatch else "criteria_matched")
            preview = self._previews[case["case_id"]]
            items.append({"preview": preview, "relation": relation, "criteria": criteria,
                          "review_issues": self._discovery_issues(case, preview),
                          "search_eligibility": self._discovery_search_gate(preview, query), "execution_authorized": False})
        rank = {"criteria_matched": 0, "related_model": 1, "conflicting": 2, "unconfirmed": 3}
        items.sort(key=lambda item: (rank[item["relation"]],
                   -sum(criterion["status"] == "matched" for criterion in item["criteria"].values()),
                   item["preview"]["case_id"]))
        return self._response(self._wrapper("fcc_report_case_discovery", query=query,
            status="review_items" if items else "no_discovery_items",
            reason_codes=[] if items else ["no_related_review_case"], items=items))

    @_public("fcc_case_invalid_intake")
    def match_intake(self, projected_summary, query):
        query = self._query(query)
        code = "fcc_case_invalid_intake"
        projection = _plain(projected_summary, code=code, byte_limit=8 * _MIB, string_limit=_MIB)
        if type(projection) is not dict or type(projection.get("facts")) is not dict:
            _fail(code)
        facts = projection["facts"]
        if len(facts) > 64:
            _fail("fcc_case_limit_exceeded")
        questions = projection.get("questions", [])
        _list(questions, 200, code=code)
        reasons, values, statuses = set(), {}, {}
        for field in ("product_type", "market", "model"):
            fact = facts.get(field)
            values[field], statuses[field] = None, None
            if fact is None:
                continue
            if type(fact) is not dict or not {"value", "status"} <= set(fact) or set(fact) - {"value", "status", "event_id"}:
                _fail(code)
            _text(fact["value"], 4000, code=code)
            _choice(fact["status"], {"explicit", "inferred", "uncertain", "user_confirmed"}, code)
            if "event_id" in fact:
                if type(fact["event_id"]) is int:
                    _integer(fact["event_id"], 1, code=code)
                else:
                    _id(fact["event_id"], code=code)
            if fact["status"] == "user_confirmed" and "event_id" not in fact:
                _fail(code)
            statuses[field] = fact["status"]
            if fact["status"] in {"explicit", "user_confirmed"}:
                values[field] = fact["value"].strip()
        for question in questions:
            if type(question) is not dict or type(question.get("key")) is not str:
                _fail(code)
            if question["key"] == "product_identity":
                reasons.add("intake_identity_unresolved")
        if values["product_type"] is None:
            reasons.add("intake_product_unconfirmed")
        elif query["product_family"] is not None and _normalize(values["product_type"]) != _normalize(query["product_family"]):
            reasons.add("intake_product_conflict")
        if values["market"] is None:
            reasons.add("intake_market_unconfirmed")
        elif _normalize(values["market"]) not in {"fcc", "us", "usa", "united states", "united states of america", "미국"}:
            reasons.add("intake_market_not_fcc")
        if query["model"] is not None:
            if values["model"] is None:
                reasons.add("intake_model_unconfirmed")
            elif _normalize(query["model"]) != _normalize(values["model"]):
                reasons.add("intake_model_conflict")
        binding = {"product_family": values["product_type"], "market": values["market"],
                   "model": values["model"], "fact_statuses": statuses}
        return self._matches(query, binding=binding, reasons=reasons)

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
           string_limit=16384, detach=True):
    stack, nodes, size = [(value, 0)], 0, 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > 50000 or depth > depth_limit:
            _fail("fcc_case_limit_exceeded")
        kind = type(item)
        if kind is dict:
            if nodes + len(stack) + 2 * len(item) > 50000:
                _fail("fcc_case_limit_exceeded")
            size += 2 + max(0, 2 * len(item) - 1)
            for key, child in item.items():
                if type(key) is not str:
                    _fail(code)
                stack.append((key, depth + 1)); stack.append((child, depth + 1))
        elif kind is list:
            if nodes + len(stack) + len(item) > 50000:
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


def _decode(raw):
    if type(raw) not in (str, bytes):
        _fail()
    try:
        payload = raw.encode("utf-8") if type(raw) is str else raw
        if len(payload) > _PACKET_BYTES:
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


class FccReportCaseCatalog:
    @_public("fcc_case_invalid_packet")
    def __init__(self, packet, pdf_sources):
        packet = _plain(packet)
        _keys(packet, {"schema_version", "corpus_id", "scope", "searches", "documents", "cases"})
        if type(packet["schema_version"]) is not int or packet["schema_version"] != 1:
            _fail()
        _id(packet["corpus_id"])
        self._packet = packet
        self._validate_scope_searches()
        self._validate_documents()
        self._validate_cases()
        blobs = self._sources(pdf_sources)
        self._extractions, self._documents = {}, {}
        remaining_pages, remaining_chars = 800, 4000000
        for document in packet["documents"]:
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
    def from_json(cls, packet_json, pdf_sources):
        return cls(_decode(packet_json), pdf_sources)

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

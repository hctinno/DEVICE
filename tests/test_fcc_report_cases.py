"""Synthetic report cases; no collected source, customer value, or actual AI."""

from copy import deepcopy
import hashlib
import inspect
from io import BytesIO
import json
import logging
import math
import unittest
from unittest import mock

from pypdf import PdfReader, PdfWriter
from pypdf._page import PageObject
from pypdf.constants import UserAccessPermissions
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject

from labflow import fcc_report_cases as cases
from labflow.document_extract import extract_document, page_citation
from labflow.intake_analysis import project_analysis
from tests.test_document_extract import synthetic_pdf


COMMON = {"schema_version", "kind", "corpus_id", "execution_mode", "synthetic", "validation_scope", "verification"}
PREVIEW = {"case_id", "report_group_id", "report_number", "revision", "issuer_class", "issue_date",
           "scope_status", "fcc_ids", "product_family", "manufacturer", "models", "rules", "methods",
           "equipment_models", "review_status", "document_ids", "evaluation_group"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fixture():
    lines = ["SYNTHETIC REPORT: SYN-001", "Revision R1", "Synthetic HCT Legal Company",
             "1 Synthetic Road", "Issued 2025-05-01", "Product sensor_node", "Manufacturer Example Devices",
             "Model MODEL-A", "Rule 47 CFR 15.247", "Method ANSI C63.10-2020", "FCC ID SYN-AA",
             "Equipment METER-A", "Power 0 dBm", "Disabled False", "<script>PRIVATE-SYNTHETIC</script>"]
    payload = synthetic_pdf(["\n".join(lines), "Unrelated second page\nOther value"])
    source_hash = digest(payload)
    extracted = extract_document(payload, "DOC-A.pdf")
    claims = []

    def claim(field, value, line, *, basis="report_fact", status="reviewed", unit=None):
        citation = page_citation(extracted, 1, line, line)
        evidence = {"document_id": "DOC-A", "source_sha256": source_hash, "file_page": 1,
                    "printed_page": "unknown", "table": None, "row": None, "column": None,
                    "footnotes": [], "text_sha256": citation["text_sha256"], "line_start": line,
                    "line_end": line, "quote": citation["quote"]}
        return {"claim_id": "CL-" + str(len(claims) + 1), "field": field, "value": value,
                "unit": unit, "status": status, "basis": basis, "evidence": [evidence]}

    for field, value, line, basis in [
        ("report.number", "SYN-001", 1, "report_fact"), ("report.revision", "R1", 2, "report_fact"),
        ("issuer.classification", "hct_korea", 3, "developer_inference"),
        ("issuer.legal_name", "Synthetic HCT Legal Company", 3, "report_fact"),
        ("issuer.address", "1 Synthetic Road", 4, "report_fact"),
        ("report.issue_date", "2025-05-01", 5, "report_fact"),
        ("product.family", "sensor_node", 6, "report_fact"),
        ("product.manufacturer", "Example Devices", 7, "report_fact"),
        ("product.models", ["MODEL-A"], 8, "report_fact"),
        ("method.rules", ["47 CFR 15.247"], 9, "report_fact"),
        ("method.references", ["ANSI C63.10-2020"], 10, "standard_reference_only"),
        ("report.fcc_ids", ["SYN-AA"], 11, "report_fact"),
        ("equipment.models", ["METER-A"], 12, "report_fact"),
    ]:
        claims.append(claim(field, value, line, basis=basis))
    packet = {
        "schema_version": 1, "corpus_id": "SYNTHETIC-CORPUS-021",
        "scope": {"issue_date_from": "2025-01-01", "cutoff_at": "2026-10-24T12:00:00+09:00",
                  "timezone": "Asia/Seoul", "population_status": "unconfirmed",
                  "search_scope_notes": ["Synthetic packet only"], "unverified_ranges": ["Population unknown"],
                  "synthetic": True},
        "searches": [{"search_id": "SEARCH-A", "institution_scope": "hct_korea",
                      "query": "Synthetic query", "url": "https://example.invalid/search",
                      "searched_at": "2026-10-24T11:00:00+09:00", "status": "blocked",
                      "page_start": None, "page_end": None, "result_limit": None,
                      "candidate_count": None, "unverified_ranges": ["Unsearched scope"], "notes": None}],
        "documents": [{"document_id": "DOC-A", "sha256": source_hash, "size_bytes": len(payload),
                       "physical_pages": 2,
                       "exhibits": [{"exhibit_id": "EX-A", "fcc_id": "SYN-AA", "application_id": None,
                                     "exhibit_type": "synthetic report", "url": "https://example.invalid/report.pdf",
                                     "source_kind": "mirror", "accessed_at": "2026-10-24T11:00:00+09:00",
                                     "official_match_status": "blocked", "official_url": None,
                                     "search_ids": ["SEARCH-A"]}],
                       "rights": {"status": "private_only", "notes": None,
                                  "public_redistribution_allowed": False, "external_model_use_allowed": False}}],
        "cases": [{"case_id": "CASE-A", "report_group_id": "REPORT-GROUP-A", "document_ids": ["DOC-A"],
                   "claims": claims, "relations": [], "reuse_group_ids": ["REUSE-A"]}],
    }
    return packet, {source_hash: payload}, claim


class FccReportCaseTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.sources, self.claim_factory = fixture()
        self.query = {"product_family": "sensor_node", "rule": "47 CFR 15.247",
                      "method": "ANSI C63.10-2020", "model": "MODEL-A"}

    def catalog(self):
        return cases.FccReportCaseCatalog(self.packet, self.sources)

    def claim(self, field):
        return next(claim for claim in self.packet["cases"][0]["claims"] if claim["field"] == field)

    def error(self, code, operation=None):
        with self.assertRaises(cases.FccReportCaseError) as caught:
            (operation or self.catalog)()
        error = caught.exception
        self.assertEqual(error.code, code)
        self.assertEqual(str(error), code)
        self.assertEqual(error.args, (code,))
        self.assertIsNone(error.__context__)
        self.assertNotIn("PRIVATE-SYNTHETIC", repr(error))

    def replace_pdf(self, payload, pages):
        document = self.packet["documents"][0]
        original = document["sha256"]
        new_hash = digest(payload)
        document.update(sha256=new_hash, size_bytes=len(payload), physical_pages=pages)
        self.sources = {new_hash: payload}
        for case in self.packet["cases"]:
            for claim in case["claims"]:
                for evidence in claim["evidence"]:
                    if evidence["source_sha256"] == original:
                        evidence["source_sha256"] = new_hash

    def permission_pdf(self, user_password="", owner_password="SYNTHETIC-OWNER"):
        writer = PdfWriter()
        writer.append(PdfReader(BytesIO(next(iter(self.sources.values())))))
        writer.encrypt(user_password, owner_password=owner_password)
        stream = BytesIO(); writer.write(stream); writer.close()
        return stream.getvalue()

    def projection(self):
        return {"facts": {"product_type": {"value": "sensor_node", "status": "explicit"},
                          "market": {"value": "FCC", "status": "explicit"},
                          "model": {"value": "MODEL-A", "status": "explicit"}}, "questions": []}

    def test_summary_and_case_exact_contract_and_private_literal(self):
        catalog = self.catalog()
        summary = catalog.summary()
        self.assertEqual(set(summary), COMMON | {"scope", "searches", "counts", "documents", "case_previews"})
        self.assertEqual(summary["kind"], "fcc_report_case_summary")
        self.assertEqual(summary["execution_mode"], "report_derived")
        self.assertTrue(summary["synthetic"])
        self.assertTrue(all(value is False for value in summary["verification"].values()))
        self.assertEqual(len(summary["verification"]), 5)
        self.assertIsNone(summary["counts"]["candidate_count"])
        self.assertEqual(summary["counts"]["acquired_unique_pdfs"], 1)
        self.assertEqual(summary["counts"]["model_evaluated_cases"], 0)
        self.assertEqual(len(summary["counts"]), 15)
        preview = summary["case_previews"][0]
        self.assertEqual(set(preview), PREVIEW)
        self.assertEqual(preview["issuer_class"], "hct_korea")
        self.assertEqual(preview["scope_status"], "in_scope")
        self.assertTrue(preview["evaluation_group"]["eligible"])
        self.assertIn("source:" + self.packet["documents"][0]["sha256"], preview["evaluation_group"]["keys"])
        detail = catalog.case("CASE-A")
        self.assertEqual(set(detail), COMMON | {"case", "documents"})
        self.assertEqual(detail["kind"], "fcc_report_case")
        self.assertEqual(set(detail["case"]), set(self.packet["cases"][0]) | {"preview"})
        self.assertEqual(len(detail["documents"][0]), 8)
        self.assertEqual(len(detail["documents"][0]["page_index"][0]), 5)
        evidence = detail["case"]["claims"][0]["evidence"][0]
        self.assertEqual(len(evidence), 13)
        self.assertTrue(evidence["literal_verified"])
        self.assertEqual(evidence["quote"], "SYNTHETIC REPORT: SYN-001")
        self.assertNotIn("text", detail["documents"][0]["page_index"][0])
        self.assertNotIn("filename", detail["documents"][0])

    def test_input_and_output_are_detached(self):
        catalog = self.catalog()
        expected = catalog.case("CASE-A")
        self.claim("report.number")["value"] = "changed input"
        self.sources.clear()
        result = catalog.case("CASE-A")
        result["case"]["claims"][0]["evidence"][0]["quote"] = "changed output"
        result["documents"][0]["rights"]["status"] = "changed"
        self.assertEqual(catalog.case("CASE-A"), expected)

    def test_query_methods_do_no_io_or_reextraction(self):
        catalog = self.catalog()
        with mock.patch.object(cases, "extract_document", side_effect=AssertionError("reparse")), \
                mock.patch("builtins.open", side_effect=AssertionError("file I/O")), \
                mock.patch("sqlite3.connect", side_effect=AssertionError("DB")), \
                mock.patch("socket.socket", side_effect=AssertionError("network")):
            catalog.summary()
            catalog.case("CASE-A")
            catalog.search(self.query)
            catalog.match_intake(self.projection(), self.query)

    def test_same_physical_pdf_preserves_multiple_exhibits_and_cases(self):
        document = self.packet["documents"][0]
        extra = deepcopy(document["exhibits"][0]); extra["exhibit_id"] = "EX-B"
        document["exhibits"].append(extra)
        second = deepcopy(self.packet["cases"][0]); second["case_id"] = "CASE-B"
        second["relations"] = [{"relation_id": "REL-A", "kind": "revision_of", "target_case_id": "CASE-A",
                                "external_target": None, "status": "resolved"}]
        self.packet["cases"].append(second)
        result = self.catalog().summary()
        self.assertEqual(result["counts"]["acquired_unique_pdfs"], 1)
        self.assertEqual(result["counts"]["exhibit_relations"], 2)
        self.assertEqual(result["counts"]["case_count"], 2)

    def test_source_type_set_hash_and_size_must_match(self):
        original = self.sources.copy()
        for sources in ({}, {"0" * 64: next(iter(original.values()))},
                        {key: bytearray(value) for key, value in original.items()},
                        {**original, "0" * 64: b"unlisted"}):
            with self.subTest(keys=len(sources)):
                self.error("fcc_case_invalid_sources", lambda: cases.FccReportCaseCatalog(self.packet, sources))
        self.packet["documents"][0]["size_bytes"] += 1
        self.error("fcc_case_invalid_sources")

    def test_invalid_topkeys_bool_integer_and_custom_objects(self):
        for mutate in (lambda p: p.update(extra=True), lambda p: p.update(schema_version=True),
                       lambda p: p["documents"][0].update(physical_pages=True),
                       lambda p: p["scope"].update(population_status="complete"),
                       lambda p: p["scope"].update(timezone="UTC"),
                       lambda p: p["cases"][0]["claims"][0].update(value=object())):
            packet = deepcopy(self.packet); mutate(packet)
            with self.subTest(mutate=mutate.__code__.co_firstlineno):
                self.error("fcc_case_invalid_packet", lambda: cases.FccReportCaseCatalog(packet, self.sources))

    def test_json_text_rejects_duplicate_nonfinite_and_invalid_utf8(self):
        for raw in (b"\xff", '{"schema_version":1,"schema_version":1}', '{"value":NaN}',
                    '{"value":Infinity}', '{"value":1e9999}'):
            with self.subTest(raw=str(raw)[:25]):
                self.error("fcc_case_invalid_packet", lambda: cases.FccReportCaseCatalog.from_json(raw, self.sources))
        catalog = cases.FccReportCaseCatalog.from_json(json.dumps(self.packet), self.sources)
        self.assertEqual(catalog.summary()["corpus_id"], self.packet["corpus_id"])

    def test_depth_and_source_size_are_bounded_before_parser(self):
        value = "leaf"
        for _ in range(20): value = [value]
        self.packet["cases"][0]["claims"][0]["value"] = value
        with mock.patch.object(cases, "extract_document", side_effect=AssertionError("parser called")):
            self.error("fcc_case_limit_exceeded")
        self.packet, self.sources, _ = fixture()
        payload = b"%PDF-" + b" " * (16 * 1024 * 1024)
        self.replace_pdf(payload, 1)
        with mock.patch.object(cases, "extract_document", side_effect=AssertionError("parser called")):
            self.error("fcc_case_limit_exceeded")

    def test_evidence_quote_line_and_footnote_limits_are_checked_before_parser(self):
        original = deepcopy(self.packet)
        for changes in ({"quote": "x" * 8193}, {"line_end": 41}, {"footnotes": ["note"] * 17}):
            self.packet = deepcopy(original)
            self.claim("report.number")["evidence"][0].update(changes)
            with self.subTest(changes=list(changes)), \
                    mock.patch.object(cases, "extract_document", side_effect=AssertionError("parser called")) as parser:
                self.error("fcc_case_limit_exceeded" if "footnotes" in changes else "fcc_case_invalid_evidence")
                parser.assert_not_called()

    def test_repeated_non_identifier_notes_and_footnotes_are_preserved(self):
        self.packet["scope"]["search_scope_notes"] = ["Same note", "Same note"]
        self.claim("report.number")["evidence"][0]["footnotes"] = ["Same footnote", "Same footnote"]
        catalog = self.catalog()
        self.assertEqual(catalog.summary()["scope"]["search_scope_notes"], ["Same note", "Same note"])
        self.assertEqual(catalog.case("CASE-A")["case"]["claims"][0]["evidence"][0]["footnotes"],
                         ["Same footnote", "Same footnote"])

    def test_html_malformed_encrypted_and_wrong_physical_pages_are_not_verified(self):
        original_packet, original_sources = deepcopy(self.packet), self.sources.copy()
        for payload in (b"<html>not a PDF</html>", b"%PDF-1.7\nmalformed"):
            self.packet, self.sources = deepcopy(original_packet), original_sources.copy()
            self.replace_pdf(payload, 1)
            self.error("fcc_case_pdf_invalid")
        self.packet, self.sources = deepcopy(original_packet), original_sources.copy()
        self.replace_pdf(self.permission_pdf(user_password="SYNTHETIC-SECRET"), 2)
        self.error("fcc_case_pdf_invalid")
        self.packet, self.sources = deepcopy(original_packet), original_sources.copy()
        self.packet["documents"][0]["physical_pages"] = 3
        self.error("fcc_case_pdf_invalid")

    def test_public_empty_user_permission_pdf_is_read_from_unchanged_original_bytes(self):
        payload = self.permission_pdf()
        self.replace_pdf(payload, 2)
        before = digest(payload)
        self.assertEqual(extract_document(payload, "private-synthetic.pdf")["status"], "encrypted")
        result = self.catalog().case("CASE-A")
        document = result["documents"][0]
        self.assertEqual(document["sha256"], before)
        self.assertEqual(digest(payload), before)
        self.assertEqual(document["extraction"]["parser"]["name"], "pypdf-public-empty-user-password")
        self.assertIn({"code": "public_empty_user_password_read", "file_page": None}, document["extraction"]["issues"])
        self.assertEqual(document["extraction"]["total_pages"], 2)
        self.assertTrue(document["page_index"][0]["citable"])
        self.assertTrue(result["case"]["claims"][0]["evidence"][0]["literal_verified"])
        self.assertEqual(extract_document(payload, "private-synthetic.pdf")["status"], "encrypted")

    def test_permission_adapter_rejects_secret_user_owner_only_and_private_sources(self):
        packet, sources = deepcopy(self.packet), self.sources.copy()
        for user, owner, source_kind in (("SYNTHETIC-SECRET", "SYNTHETIC-OWNER", "mirror"),
                                         ("SYNTHETIC-SECRET", "", "mirror"), ("", "SYNTHETIC-OWNER", "existing_user")):
            self.packet, self.sources = deepcopy(packet), sources.copy()
            self.replace_pdf(self.permission_pdf(user, owner), 2)
            self.packet["documents"][0]["exhibits"][0]["source_kind"] = source_kind
            with self.subTest(user_empty=not user, owner_empty=not owner, source_kind=source_kind):
                self.error("fcc_case_pdf_invalid")

    def test_permission_adapter_preserves_page_limits_and_warning_rejection(self):
        self.replace_pdf(self.permission_pdf(), 2)
        result = cases._public_read_pdf(next(iter(self.sources.values())), "DOC-A.pdf",
                                        cases.ExtractionLimits(max_pages=1))
        self.assertEqual(result["processed_pages"], 1)
        self.assertEqual(result["status"], "partial")
        self.assertIn({"code": "page_limit"}, result["issues"])
        with mock.patch.object(cases._extract, "_warnings_observable", return_value=False):
            self.error("fcc_case_invalid_evidence")

    def test_permission_adapter_verifies_only_once_without_pdf_rewrite(self):
        from pypdf._encryption import Encryption
        self.replace_pdf(self.permission_pdf(), 2)
        original, calls = Encryption.verify, []
        def once(encryption, password, **kwargs):
            calls.append(password)
            return original(encryption, password, **kwargs)
        with mock.patch.object(Encryption, "verify", new=once), \
                mock.patch.object(PdfWriter, "write", side_effect=AssertionError("PDF rewrite")), \
                mock.patch.object(PdfReader, "decrypt", side_effect=AssertionError("retry")):
            result = self.catalog().summary()
        self.assertEqual(calls, [""])
        self.assertEqual(result["counts"]["complete_text_pdfs"], 1)

    def test_permission_adapter_keeps_content_and_retained_character_limits(self):
        self.replace_pdf(self.permission_pdf(), 2)
        payload = next(iter(self.sources.values()))
        for limits, issue in ((cases.ExtractionLimits(max_page_content_bytes=1), "content_limit"),
                              (cases.ExtractionLimits(max_output_chars=10), "output_limit")):
            with self.subTest(issue=issue):
                result = cases._public_read_pdf(payload, "DOC-A.pdf", limits)
                self.assertIn(issue, [row["code"] for row in result["issues"]])
                self.assertFalse(result["complete"])
                self.assertFalse(cases.FccReportCaseCatalog._citable(result, result["pages"][0]))

    def test_evidence_binds_source_page_hash_lines_and_full_quote(self):
        original = deepcopy(self.packet)
        for changes in ({"source_sha256": "0" * 64}, {"file_page": 2}, {"text_sha256": "0" * 64},
                        {"line_start": True}, {"line_start": 0}, {"line_end": 9999},
                        {"quote": "SYN-001"}, {"document_id": "UNKNOWN"}):
            self.packet = deepcopy(original)
            self.packet["cases"][0]["claims"][0]["evidence"][0].update(changes)
            with self.subTest(keys=list(changes)):
                self.error("fcc_case_invalid_evidence")

    def test_zero_float_zero_and_false_are_valid_report_values(self):
        for index, value in enumerate((0, 0.0, False)):
            claim = deepcopy(self.claim("report.number"))
            claim.update(claim_id="VALUE-" + str(index), field="result.value_" + str(index), value=value)
            self.packet["cases"][0]["claims"].append(claim)
        result = self.catalog().case("CASE-A")["case"]["claims"][-3:]
        self.assertEqual([type(row["value"]) for row in result], [int, float, bool])
        self.assertEqual([row["value"] for row in result], [0, 0.0, False])

    def test_missing_values_and_failed_extraction_are_not_zero_defaults(self):
        original = deepcopy(self.packet)
        for value in (None, "", "  ", [], {}):
            self.packet = deepcopy(original); self.claim("report.number")["value"] = value
            with self.subTest(value_type=type(value).__name__): self.error("fcc_case_invalid_packet")
        self.packet = deepcopy(original)
        self.claim("product.family").update(status="extraction_failed", value=None, evidence=[])
        detail = self.catalog().case("CASE-A")
        self.assertIsNone(detail["case"]["preview"]["product_family"])
        self.assertIsNone(next(c for c in detail["case"]["claims"] if c["field"] == "product.family")["value"])

    def test_issuer_inference_requires_both_reviewed_legal_name_and_address(self):
        self.assertEqual(self.catalog().summary()["case_previews"][0]["issuer_class"], "hct_korea")
        for field in ("issuer.legal_name", "issuer.address"):
            original = deepcopy(self.packet)
            self.claim(field)["status"] = "extracted"
            preview = self.catalog().summary()["case_previews"][0]
            self.assertEqual(preview["issuer_class"], "unknown")
            self.packet = original
        self.packet["cases"][0]["claims"] = [row for row in self.packet["cases"][0]["claims"]
                                                if row["field"] != "issuer.classification"]
        self.assertEqual(self.catalog().summary()["case_previews"][0]["issuer_class"], "unknown")

    def test_scalar_preview_requires_a_scalar_string_not_singleton_array(self):
        original = deepcopy(self.packet)
        for field, preview_key in (("report.number", "report_number"), ("report.issue_date", "issue_date"),
                                   ("product.family", "product_family"), ("issuer.classification", "issuer_class")):
            self.packet = deepcopy(original)
            self.claim(field)["value"] = [self.claim(field)["value"]]
            preview = self.catalog().summary()["case_previews"][0]
            with self.subTest(field=field):
                self.assertEqual(preview[preview_key], "unknown" if field == "issuer.classification" else None)
        self.assertEqual(self.catalog().summary()["case_previews"][0]["models"], ["MODEL-A"])

    def test_conflicting_date_claim_keeps_scope_pending_even_with_reviewed_date(self):
        claim = deepcopy(self.claim("report.issue_date"))
        claim.update(claim_id="DATE-CONFLICT", status="conflicting", value=["2025-05-01", "2025-06-01"])
        self.packet["cases"][0]["claims"].append(claim)
        preview = self.catalog().summary()["case_previews"][0]
        self.assertIsNone(preview["issue_date"])
        self.assertEqual(preview["scope_status"], "pending")
        self.assertEqual(preview["review_status"], "conflicting")

    def test_unknown_date_conflict_past_and_future_remain_separate(self):
        original = deepcopy(self.packet)
        for value, status, scope in ((None, "not_reported", "pending"), ("2024-12-31", "reviewed", "out_of_range"),
                                     ("2027-01-01", "reviewed", "future")):
            self.packet = deepcopy(original)
            claim = self.claim("report.issue_date"); claim.update(value=value, status=status)
            if value is None: claim["evidence"] = []
            catalog = self.catalog(); self.assertEqual(catalog.summary()["case_previews"][0]["scope_status"], scope)
            self.assertNotEqual(catalog.search(self.query)["status"], "candidates")
        self.packet = deepcopy(original)
        conflicting = deepcopy(self.claim("report.issue_date")); conflicting.update(claim_id="DATE-2", value="2025-06-01")
        self.packet["cases"][0]["claims"].append(conflicting)
        preview = self.catalog().summary()["case_previews"][0]
        self.assertEqual(preview["scope_status"], "pending")
        self.assertEqual(preview["review_status"], "conflicting")

    def test_image_only_preserves_state_and_has_no_citable_page(self):
        self.replace_pdf(synthetic_pdf([None], images={0}), 1)
        self.packet["cases"][0]["claims"] = []
        result = self.catalog().summary()
        self.assertEqual(result["documents"][0]["extraction"]["status"], "image_only")
        self.assertFalse(result["documents"][0]["page_index"][0]["citable"])
        self.assertEqual(result["counts"]["complete_text_pdfs"], 0)

    def test_partial_document_can_cite_clean_page_but_not_image_page(self):
        text = extract_document(next(iter(self.sources.values())), "DOC-A.pdf")["pages"][0]["text"]
        self.replace_pdf(synthetic_pdf([text, None], images={1}), 2)
        result = self.catalog().case("CASE-A")
        self.assertEqual(result["documents"][0]["extraction"]["status"], "partial")
        self.assertTrue(result["documents"][0]["page_index"][0]["citable"])
        self.packet["cases"][0]["claims"][0]["evidence"][0]["file_page"] = 2
        self.error("fcc_case_invalid_evidence")

    def test_warning_on_cited_page_is_not_qualified_by_retained_text_alone(self):
        def warning(*args, **kwargs):
            result = extract_document(*args, **kwargs)
            result.update(status="partial", complete=False)
            result["issues"].append({"code": "parser_warning", "page_number": 1})
            return result
        with mock.patch.object(cases, "extract_document", side_effect=warning):
            self.error("fcc_case_invalid_evidence")

    def test_search_requires_context_and_exact_product_rule_and_edition(self):
        catalog = self.catalog()
        result = catalog.search(self.query)
        self.assertEqual(set(result), COMMON | {"query", "status", "reason_codes", "intake_binding", "matches"})
        self.assertEqual(result["kind"], "fcc_report_case_matches")
        self.assertEqual(result["status"], "candidates")
        self.assertEqual(result["matches"][0]["model_relation"], "exact_model")
        for field in ("product_family", "rule", "method"):
            query = dict(self.query); query[field] = None
            with self.subTest(field=field): self.assertEqual(catalog.search(query)["status"], "insufficient_evidence")
        for changes in ({"product_family": "smartphone"}, {"method": "ANSI C63.10-2013"}, {"rule": "47 CFR 15.249"}):
            query = {**self.query, **changes}
            self.assertEqual(catalog.search(query)["status"], "no_match")
        query = {key: (" " + value.swapcase() + " ") for key, value in self.query.items()}
        self.assertEqual(catalog.search(query)["status"], "candidates")

    def test_other_model_is_related_family_and_insufficient_actual_model_evidence(self):
        result = self.catalog().search({**self.query, "model": "MODEL-B"})
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIn("exact_model_case_missing", result["reason_codes"])
        self.assertEqual(result["matches"][0]["model_relation"], "related_family")

    def test_match_intake_uses_only_explicit_confirmed_fcc_context(self):
        catalog, projection = self.catalog(), self.projection()
        self.assertEqual(catalog.match_intake(projection, self.query)["status"], "candidates")
        for field in ("product_type", "market", "model"):
            changed = deepcopy(projection); changed["facts"][field]["status"] = "inferred"
            self.assertEqual(catalog.match_intake(changed, self.query)["status"], "insufficient_evidence")
        for market in ("CE", "Korea", "US and EU"):
            changed = deepcopy(projection); changed["facts"]["market"]["value"] = market
            self.assertEqual(catalog.match_intake(changed, self.query)["status"], "insufficient_evidence")
        projection["facts"]["model"].update(status="user_confirmed", event_id=1)
        self.assertEqual(catalog.match_intake(projection, self.query)["status"], "candidates")

    def test_intake_conflicting_product_model_and_identity_are_not_assumed(self):
        catalog = self.catalog()
        for field, value in (("product_type", "router"), ("model", "OTHER")):
            projection = self.projection(); projection["facts"][field]["value"] = value
            self.assertEqual(catalog.match_intake(projection, self.query)["status"], "insufficient_evidence")
        projection = self.projection(); projection["questions"] = [{"key": "product_identity", "message": "Unknown"}]
        self.assertEqual(catalog.match_intake(projection, self.query)["status"], "insufficient_evidence")

    def test_real_project_analysis_projection_is_read_only_compatible(self):
        analysis = {"identity": "single", "missing_fields": [], "facts": [
            {"field": field, "value": value, "status": "explicit", "evidence": [{"role": "request"}]}
            for field, value in (("product_type", "sensor_node"), ("market", "FCC"), ("model", "MODEL-A"))]}
        projection = project_analysis(analysis, [], {}, delegated=False, deferred=False)
        before = deepcopy(projection)
        result = self.catalog().match_intake(projection, self.query)
        self.assertEqual(result["status"], "candidates")
        self.assertEqual(projection, before)

    def test_unknown_report_and_reuse_groups_never_become_independent_ids(self):
        self.packet["cases"][0].update(report_group_id=None, reuse_group_ids=[])
        group = self.catalog().summary()["case_previews"][0]["evaluation_group"]
        self.assertFalse(group["eligible"])
        self.assertIn("report_group_id", group["missing"])
        self.assertIn("reuse_group_ids", group["missing"])
        self.assertFalse(any(value.startswith("report:") for value in group["keys"]))

    def test_unsafe_urls_and_unknown_relation_targets_are_not_accepted(self):
        original = deepcopy(self.packet)
        for url in ("javascript:alert(1)", "file:///PRIVATE-SYNTHETIC.pdf", "https://user:password@example.invalid/a"):
            self.packet = deepcopy(original); self.packet["documents"][0]["exhibits"][0]["url"] = url
            self.error("fcc_case_invalid_packet")
        self.packet = deepcopy(original)
        self.packet["cases"][0]["relations"] = [{"relation_id": "REL-A", "kind": "revision_of",
            "target_case_id": "MISSING", "external_target": None, "status": "resolved"}]
        self.error("fcc_case_invalid_packet")

    def test_http_url_rejects_invalid_port(self):
        self.packet["documents"][0]["exhibits"][0]["url"] = "https://example.invalid:invalid/a"
        self.error("fcc_case_invalid_packet")

    def test_missing_parser_never_produces_a_verified_document(self):
        result = extract_document(next(iter(self.sources.values())), "DOC-A.pdf")
        result.update(status="parser_unavailable", total_pages=None, processed_pages=0, complete=False)
        with mock.patch.object(cases, "extract_document", return_value=result):
            self.error("fcc_case_extraction_unavailable")

    def test_global_page_budget_stops_before_a_fifth_200_page_extraction(self):
        original = deepcopy(self.packet["documents"][0])
        self.packet.update(documents=[], cases=[])
        self.sources.clear()
        for index in range(5):
            payload = synthetic_pdf(["SYNTHETIC doc " + str(index)] * 201)
            document = deepcopy(original)
            document.update(document_id="DOC-" + str(index), sha256=digest(payload),
                            size_bytes=len(payload), physical_pages=201)
            self.packet["documents"].append(document)
            self.sources[document["sha256"]] = payload
        with mock.patch.object(cases, "extract_document", wraps=extract_document) as parser:
            self.error("fcc_case_limit_exceeded")
        self.assertEqual(parser.call_count, 4)

    def test_query_case_and_intake_errors_are_fixed(self):
        catalog = self.catalog()
        self.error("fcc_case_not_found", lambda: catalog.case("MISSING"))
        self.error("fcc_case_invalid_query", lambda: catalog.case(None))
        self.error("fcc_case_invalid_query", lambda: catalog.search({**self.query, "extra": True}))
        self.error("fcc_case_invalid_query", lambda: catalog.search({**self.query, "model": False}))
        self.error("fcc_case_invalid_intake", lambda: catalog.match_intake({"facts": []}, self.query))

    def test_empty_packet_keeps_population_unknown(self):
        self.packet.update(documents=[], cases=[])
        self.sources.clear()
        result = self.catalog().summary()
        self.assertEqual(result["counts"]["acquired_unique_pdfs"], 0)
        self.assertIsNone(result["counts"]["candidate_count"])
        self.assertEqual(result["scope"]["population_status"], "unconfirmed")


class FccReportCaseDiscoveryTests(unittest.TestCase):
    """028 contract RED; existing 021 selectors keep their original meaning."""

    def setUp(self):
        self.packet, self.sources, _ = fixture()
        self.query = {"product_family": "sensor_node", "rule": "47 CFR 15.247",
                      "method": "ANSI C63.10-2020", "model": "MODEL-A"}
        self.assertTrue(callable(getattr(cases.FccReportCaseCatalog, "discover", None)), "028 discover API is absent")

    def catalog(self):
        return cases.FccReportCaseCatalog(self.packet, self.sources)

    def test_discovery_exact_wrapper_and_projection_keys(self):
        result = self.catalog().discover(self.query)
        self.assertEqual(set(result), COMMON | {"query", "status", "reason_codes", "items"})
        self.assertEqual(result["kind"], "fcc_report_case_discovery")
        self.assertEqual(result["status"], "review_items")
        item = result["items"][0]
        self.assertEqual(set(item), {"preview", "relation", "criteria", "review_issues", "search_eligibility", "execution_authorized"})
        self.assertEqual(set(item["criteria"]), set(self.query))
        self.assertEqual(item["relation"], "criteria_matched")
        self.assertEqual(item["search_eligibility"], {"eligible": True, "reason_codes": []})
        self.assertIs(item["execution_authorized"], False)
        for criterion in item["criteria"].values():
            self.assertEqual(set(criterion), {"query", "status", "reviewed_values", "matched_claim_ids", "claims"})
            for claim in criterion["claims"]:
                self.assertEqual(set(claim), {"claim_id", "status", "basis", "value", "unit", "evidence_refs"})

    def test_other_field_conflict_is_discoverable_without_opening_legacy_gates(self):
        conflict = deepcopy(self.packet["cases"][0]["claims"][0])
        conflict.update(claim_id="RESULT-CONFLICT", field="result.optional_value", status="conflicting", value=[1, 2])
        self.packet["cases"][0]["claims"].append(conflict)
        catalog = self.catalog(); before = catalog.case("CASE-A")
        self.assertEqual(catalog.search(self.query)["status"], "no_match")
        item = catalog.discover(self.query)["items"][0]
        self.assertEqual(item["preview"]["review_status"], "conflicting")
        self.assertEqual(item["relation"], "criteria_matched")
        self.assertFalse(item["search_eligibility"]["eligible"])
        self.assertIn("case_conflicting", item["search_eligibility"]["reason_codes"])
        self.assertIn("case_conflicting", item["review_issues"])
        analysis = {"identity": "single", "missing_fields": [], "facts": [
            {"field": field, "value": value, "status": "explicit", "evidence": [{"role": "request"}]}
            for field, value in (("product_type", "sensor_node"), ("market", "FCC"), ("model", "MODEL-A"))]}
        projected = project_analysis(analysis, [], {}, delegated=False, deferred=False)
        projected_before = deepcopy(projected)
        self.assertEqual(catalog.match_intake(projected, self.query)["status"], "no_match")
        self.assertEqual(projected, projected_before)
        self.assertEqual(catalog.case("CASE-A"), before)

    def test_unknown_nonstring_zero_false_and_null_are_preserved_as_unconfirmed(self):
        original = deepcopy(self.packet)
        for value, status in ((0, "reviewed"), (False, "reviewed"), (None, "extraction_failed")):
            self.packet = deepcopy(original)
            claim = next(c for c in self.packet["cases"][0]["claims"] if c["field"] == "product.family")
            claim.update(value=value, status=status)
            if value is None:
                claim["evidence"] = []
            with self.subTest(value_type=type(value).__name__):
                criterion = self.catalog().discover(self.query)["items"][0]["criteria"]["product_family"]
                self.assertEqual(criterion["status"], "unconfirmed")
                self.assertEqual(criterion["reviewed_values"], [])
                self.assertEqual(criterion["matched_claim_ids"], [])
                self.assertEqual(type(criterion["claims"][0]["value"]), type(value))
                self.assertEqual(criterion["claims"][0]["value"], value)
                self.assertEqual(criterion["claims"][0]["status"], status)

    def test_confirmed_wrong_rule_edition_and_product_are_excluded(self):
        catalog = self.catalog()
        for changes in ({"rule": "47 CFR 15.249"}, {"method": "ANSI C63.10-2013"}, {"product_family": "router"}):
            result = catalog.discover({**self.query, **changes})
            self.assertEqual(result["status"], "no_discovery_items")
            self.assertEqual(result["reason_codes"], ["no_related_review_case"])
            self.assertEqual(result["items"], [])
        item = catalog.discover({**self.query, "model": "OTHER-MODEL"})["items"][0]
        self.assertEqual(item["relation"], "related_model")
        self.assertEqual(item["criteria"]["model"]["status"], "mismatched")
        self.assertFalse(item["search_eligibility"]["eligible"])
        legacy = catalog.search({**self.query, "model": "OTHER-MODEL"})
        self.assertEqual(legacy["status"], "insufficient_evidence")
        self.assertEqual(legacy["matches"][0]["model_relation"], "related_family")
        self.assertIn("exact_model_case_missing", legacy["reason_codes"])
        partial = {"product_family": None, "rule": None, "method": None, "model": "OTHER-MODEL"}
        self.assertEqual(catalog.discover(partial)["items"], [])

    def test_partial_query_is_review_only_and_all_null_needs_context(self):
        catalog = self.catalog()
        partial = {"product_family": "sensor_node", "rule": None, "method": None, "model": None}
        item = catalog.discover(partial)["items"][0]
        self.assertEqual(item["criteria"]["rule"]["status"], "not_requested")
        self.assertFalse(item["search_eligibility"]["eligible"])
        self.assertIn("query_context_missing", item["search_eligibility"]["reason_codes"])
        self.assertEqual(catalog.search(partial)["status"], "insufficient_evidence")
        result = catalog.discover(dict.fromkeys(self.query))
        self.assertEqual(result["status"], "insufficient_context")
        self.assertEqual(result["reason_codes"], ["discovery_context_missing"])
        self.assertEqual(result["items"], [])

    def test_conflicting_criterion_preserves_alternatives_and_literal_refs(self):
        claim = deepcopy(next(c for c in self.packet["cases"][0]["claims"] if c["field"] == "product.family"))
        claim.update(claim_id="FAMILY-B", value="router")
        self.packet["cases"][0]["claims"].append(claim)
        catalog = self.catalog()
        item = catalog.discover(self.query)["items"][0]
        criterion = item["criteria"]["product_family"]
        self.assertEqual(item["relation"], "conflicting")
        self.assertEqual(criterion["status"], "conflicting")
        self.assertEqual(criterion["reviewed_values"], ["router", "sensor_node"])
        self.assertEqual(len(criterion["claims"]), 2)
        detail = {c["claim_id"]: c for c in catalog.case("CASE-A")["case"]["claims"]}
        for projected in criterion["claims"]:
            for ref in projected["evidence_refs"]:
                self.assertEqual(set(ref), {"document_id", "source_sha256", "file_page", "text_sha256",
                                            "line_start", "line_end", "literal_verified"})
                source = detail[projected["claim_id"]]["evidence"][0]
                self.assertEqual(ref, {key: source[key] for key in ref})

    def test_discovery_detached_and_no_io_reparse_or_store_changes(self):
        catalog = self.catalog()
        with mock.patch.object(cases, "extract_document", side_effect=AssertionError("reparse")), \
                mock.patch("builtins.open", side_effect=AssertionError("file")), \
                mock.patch("socket.socket", side_effect=AssertionError("network")), \
                mock.patch("sqlite3.connect", side_effect=AssertionError("DB")):
            expected = catalog.discover(self.query)
            result = catalog.discover(self.query)
            result["items"][0]["criteria"]["product_family"]["claims"][0]["value"] = "changed output"
            self.assertEqual(catalog.discover(self.query), expected)
        for query in ({**self.query, "model": False}, {**self.query, "extra": True}):
            with self.assertRaises(cases.FccReportCaseError) as caught:
                catalog.discover(query)
            self.assertEqual(caught.exception.code, "fcc_case_invalid_query")
        with mock.patch.object(cases, "_OUTPUT_BYTES", 16):
            with self.assertRaises(cases.FccReportCaseError) as caught:
                catalog.discover(self.query)
            self.assertEqual(caught.exception.code, "fcc_case_limit_exceeded")

    def test_discovery_sort_does_not_depend_on_case_or_claim_order(self):
        second = deepcopy(self.packet["cases"][0]); second["case_id"] = "CASE-B"
        self.packet["cases"].insert(0, second)
        expected = self.catalog().discover(self.query)
        self.packet["cases"].reverse()
        for case in self.packet["cases"]:
            case["claims"].reverse()
        result = self.catalog().discover(self.query)
        self.assertEqual([item["preview"]["case_id"] for item in result["items"]], ["CASE-A", "CASE-B"])
        self.assertEqual(result, expected)

    def test_equivalent_value_representative_and_evidence_refs_are_order_independent(self):
        original = next(c for c in self.packet["cases"][0]["claims"] if c["field"] == "product.family")
        duplicate = deepcopy(original); duplicate.update(claim_id="FAMILY-B", value=" SENSOR_NODE ")
        original["evidence"].append(deepcopy(self.packet["cases"][0]["claims"][0]["evidence"][0]))
        original["evidence"][0]["footnotes"] = ["Repeated", "Repeated"]
        self.packet["cases"][0]["claims"].append(duplicate)
        expected = self.catalog().discover(self.query)
        self.packet["cases"][0]["claims"].reverse()
        for claim in self.packet["cases"][0]["claims"]:
            claim["evidence"].reverse()
        catalog = self.catalog()
        self.assertEqual(catalog.discover(self.query), expected)
        criterion = expected["items"][0]["criteria"]["product_family"]
        self.assertEqual(criterion["reviewed_values"], ["SENSOR_NODE"])
        self.assertEqual([row["value"] for row in criterion["claims"]], ["sensor_node", " SENSOR_NODE "])
        original_out = next(c for c in catalog.case("CASE-A")["case"]["claims"] if c["claim_id"] == original["claim_id"])
        self.assertTrue(any(e["footnotes"] == ["Repeated", "Repeated"] for e in original_out["evidence"]))

    def test_reviewed_value_budget_accepts_128_and_rejects_129_without_truncation(self):
        claim = next(c for c in self.packet["cases"][0]["claims"] if c["field"] == "method.references")
        claim["value"] = [self.query["method"]] + ["SYNTHETIC-METHOD-" + str(i) for i in range(127)]
        result = self.catalog().discover(self.query)
        self.assertEqual(len(result["items"][0]["criteria"]["method"]["reviewed_values"]), 128)
        claim["value"].append("SYNTHETIC-METHOD-129")
        with self.assertRaises(cases.FccReportCaseError) as caught:
            self.catalog().discover(self.query)
        self.assertEqual(caught.exception.code, "fcc_case_limit_exceeded")

    def test_relation_ranking_preserves_confirmed_related_conflicting_unknown(self):
        original = self.packet["cases"][0]
        for identifier in ("CASE-B", "CASE-C", "CASE-D"):
            case = deepcopy(original); case["case_id"] = identifier
            if identifier == "CASE-B":
                next(c for c in case["claims"] if c["field"] == "product.models")["value"] = ["MODEL-B"]
            elif identifier == "CASE-C":
                duplicate = deepcopy(next(c for c in case["claims"] if c["field"] == "product.family"))
                duplicate.update(claim_id="CONFLICT-FAMILY", value="router"); case["claims"].append(duplicate)
            else:
                next(c for c in case["claims"] if c["field"] == "product.family").update(
                    status="extraction_failed", value=None, evidence=[])
            self.packet["cases"].insert(0, case)
        result = self.catalog().discover(self.query)
        self.assertEqual([(item["preview"]["case_id"], item["relation"]) for item in result["items"]],
                         [("CASE-A", "criteria_matched"), ("CASE-B", "related_model"),
                          ("CASE-C", "conflicting"), ("CASE-D", "unconfirmed")])

    def test_discovery_gate_agrees_with_exact_legacy_search_across_context_gaps(self):
        original = deepcopy(self.packet)
        for mode in ("normal", "issuer", "past", "future", "date_unknown", "conflict", "family_unknown", "partial_query", "other_model"):
            self.packet = deepcopy(original); query = dict(self.query)
            claims = self.packet["cases"][0]["claims"]
            if mode == "issuer":
                next(c for c in claims if c["field"] == "issuer.legal_name")["status"] = "extracted"
            elif mode in ("past", "future"):
                next(c for c in claims if c["field"] == "report.issue_date")["value"] = "2024-12-31" if mode == "past" else "2027-01-01"
            elif mode in ("date_unknown", "family_unknown"):
                field = "report.issue_date" if mode == "date_unknown" else "product.family"
                next(c for c in claims if c["field"] == field).update(status="not_reported", value=None, evidence=[])
            elif mode == "conflict":
                next(c for c in claims if c["field"] == "report.revision")["status"] = "conflicting"
            elif mode == "partial_query":
                query.update(rule=None, method=None, model=None)
            elif mode == "other_model":
                query["model"] = "OTHER-MODEL"
            catalog = self.catalog(); legacy = catalog.search(query); discovery = catalog.discover(query)
            expected = legacy["status"] == "candidates" and any(
                item["preview"]["case_id"] == "CASE-A" and item["model_relation"] in {"exact_model", "unspecified"}
                for item in legacy["matches"])
            with self.subTest(mode=mode):
                self.assertEqual(discovery["items"][0]["search_eligibility"]["eligible"], expected)
                self.assertFalse(discovery["items"][0]["execution_authorized"])


class FccCasePacketPreparationTests(unittest.TestCase):
    """035 metadata preparation; all source declarations are synthetic."""

    def setUp(self):
        self.assertTrue(callable(getattr(cases, "prepare_fcc_case_packet", None)), "035 memory API is absent")
        self.packet, self.pdfs, _ = fixture()
        self.packet_path, self.scope_path = "canonical/packet.json", "scope/pages.json"
        self.policy = {"schema_version": 1, "sources": {sha: {"pages": [2, 1], "mode": "accessibility",
            "basis_id": "SYNTHETIC-035", "basis_sha256": "e" * 64} for sha in self.pdfs}}

    @staticmethod
    def encoded(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def inputs(self, *, packet=None, policy=None, files=None, manifest=None):
        files = ({self.packet_path: self.encoded(self.packet if packet is None else packet),
                  self.scope_path: self.encoded(self.policy if policy is None else policy)} if files is None else files)
        manifest = ({"request_id": "DEV-HCT-FCC-CORPUS-012", "revision": "SYNTHETIC-035-v1",
                     "files": [{"path": path, "bytes": len(raw), "sha256": digest(raw)} for path, raw in files.items()]}
                    if manifest is None else manifest)
        raw = self.encoded(manifest)
        return raw, files, {"expected_manifest_sha256": digest(raw), "packet_path": self.packet_path,
                            "page_scope_path": self.scope_path}

    def prepare(self, **kwargs):
        raw, files, options = self.inputs(**kwargs)
        return cases.prepare_fcc_case_packet(raw, files, **options)

    def error(self, code, inputs=None):
        raw, files, options = inputs or self.inputs()
        with self.assertRaises(cases.FccReportCaseError) as caught:
            cases.prepare_fcc_case_packet(raw, files, **options)
        self.assertEqual((caught.exception.code, str(caught.exception), caught.exception.args), (code, code, (code,)))
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn("PRIVATE-SYNTHETIC", repr(caught.exception))

    def test_exact_preparation_contract_preserves_input_evidence12_and_false_verification(self):
        result = self.prepare()
        self.assertEqual(set(result), {"schema_version", "kind", "packet", "page_scope", "source_refs", "provenance", "verification"})
        self.assertEqual(result["schema_version"], 1); self.assertEqual(result["kind"], "fcc_case_packet_preparation")
        self.assertEqual(result["verification"], {"manifest_and_consumed_json_bytes_verified": True,
            "source_pdf_bytes_verified": False, "retained_literals_verified": False,
            "authority_or_rights_verified": False, "execution_authorized": False})
        self.assertEqual(len(result["packet"]["cases"][0]["claims"][0]["evidence"][0]), 12)
        self.assertEqual(result["source_refs"], [{key: self.packet["documents"][0][key]
            for key in ["document_id", "sha256", "size_bytes", "physical_pages"]}])
        self.assertEqual(next(iter(result["page_scope"]["sources"].values()))["pages"], [1, 2])

    def test_manifest_and_canonical_hashes_are_independently_reproducible(self):
        raw, files, options = self.inputs()
        result = cases.prepare_fcc_case_packet(raw, files, **options)
        provenance = result["provenance"]
        self.assertEqual(set(provenance), {"manifest_sha256", "consumed_files", "packet_sha256", "page_scope_sha256"})
        self.assertEqual(provenance["manifest_sha256"], digest(raw))
        self.assertEqual(provenance["consumed_files"], sorted(
            [{"path": path, "bytes": len(blob), "sha256": digest(blob)} for path, blob in files.items()], key=lambda row: row["path"]))
        for name in ["packet", "page_scope"]:
            self.assertEqual(provenance[name + "_sha256"], digest(self.encoded(result[name])))

    def test_metadata_success_does_not_verify_a_fabricated_literal_or_original_pdf(self):
        packet = deepcopy(self.packet)
        packet["cases"][0]["claims"][0]["evidence"][0].update(quote="PRIVATE-SYNTHETIC wrong literal", text_sha256="f" * 64)
        result = self.prepare(packet=packet)
        self.assertFalse(result["verification"]["retained_literals_verified"])
        with self.assertRaises(cases.FccReportCaseError) as caught:
            cases.FccReportCaseCatalog(result["packet"], self.pdfs, page_scope=result["page_scope"])
        self.assertEqual(caught.exception.code, "fcc_case_invalid_evidence")

    def test_calls_are_memory_only_without_catalog_parser_files_network_or_database(self):
        with mock.patch.object(cases.FccReportCaseCatalog, "__init__", side_effect=AssertionError("catalog")), \
                mock.patch.object(cases, "extract_document", side_effect=AssertionError("extract")), \
                mock.patch.object(cases, "_public_read_pdf", side_effect=AssertionError("full PDF")), \
                mock.patch.object(cases, "_ScopedPdf", side_effect=AssertionError("selected PDF")), \
                mock.patch("pypdf.PdfReader", side_effect=AssertionError("reader")), \
                mock.patch("builtins.open", side_effect=AssertionError("file")), \
                mock.patch("os.open", side_effect=AssertionError("descriptor")), \
                mock.patch("pathlib.Path.open", side_effect=AssertionError("path")), \
                mock.patch("socket.socket", side_effect=AssertionError("network")), \
                mock.patch("sqlite3.connect", side_effect=AssertionError("database")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("process")):
            self.assertEqual(self.prepare()["kind"], "fcc_case_packet_preparation")

    def test_expected_manifest_pin_precedes_json_interpretation(self):
        raw, files, options = self.inputs(); options["expected_manifest_sha256"] = "0" * 64
        self.error("fcc_case_invalid_sources", (b"PRIVATE-SYNTHETIC invalid JSON", files, options))
        options["expected_manifest_sha256"] = digest(b"PRIVATE-SYNTHETIC invalid JSON")
        self.error("fcc_case_invalid_packet", (b"PRIVATE-SYNTHETIC invalid JSON", files, options))

    def test_manifest_must_be_exact_bytes_and_expected_sha_strict_lower_hex(self):
        raw, files, options = self.inputs()
        class BytesChild(bytes): pass
        for bad in [raw.decode(), bytearray(raw), memoryview(raw), BytesChild(raw), None, False]:
            with self.subTest(type=type(bad).__name__): self.error("fcc_case_invalid_packet", (bad, files, options))
        for bad in [None, True, "F" * 64, "a" * 63, " a" * 32]:
            with self.subTest(sha=bad): self.error("fcc_case_invalid_packet", (raw, files, {**options, "expected_manifest_sha256": bad}))

    def test_json_blob_map_requires_exact_two_plain_keys_and_bytes(self):
        raw, files, options = self.inputs()
        class DictChild(dict): pass
        class BytesChild(bytes): pass
        for bad in [DictChild(files), [], {self.packet_path: files[self.packet_path]}, {**files, "extra.json": b"{}"},
                    {**files, self.packet_path: bytearray(files[self.packet_path])},
                    {**files, self.packet_path: BytesChild(files[self.packet_path])}]:
            with self.subTest(type=type(bad).__name__, count=len(bad)): self.error("fcc_case_invalid_sources", (raw, bad, options))

    def test_user_defined_blob_keys_are_rejected_without_hash_or_equality_callbacks(self):
        raw, files, options = self.inputs()
        collision = hash(self.packet_path)
        class HostileKey:
            calls = 0
            def __hash__(self):
                self.calls += 1
                return collision
            def __eq__(self, other):
                self.calls += 1
                return False
        key = HostileKey(); invalid = {key: b"{}", self.scope_path: files[self.scope_path]}; key.calls = 0
        self.error("fcc_case_invalid_sources", (raw, invalid, options))
        self.assertEqual(key.calls, 0)

    def test_blob_size_hash_and_missing_selected_manifest_member_are_source_errors(self):
        raw, files, options = self.inputs()
        self.error("fcc_case_invalid_sources", (raw, {**files, self.packet_path: files[self.packet_path] + b" "}, options))
        manifest = json.loads(raw)
        for change in [{"bytes": len(files[self.packet_path]) + 1}, {"sha256": "0" * 64}, {"path": "missing.json"}]:
            changed = deepcopy(manifest); changed["files"][0].update(change)
            self.error("fcc_case_invalid_sources", self.inputs(files=files, manifest=changed))

    def test_manifest_id128_minimum_two_and_maximum128_are_actual_boundaries(self):
        raw, files, options = self.inputs(); manifest = json.loads(raw)
        for revision in ["R", "R" * 128]:
            changed = {**manifest, "revision": revision}
            self.assertEqual(cases.prepare_fcc_case_packet(*self.inputs(files=files, manifest=changed)[:2],
                **self.inputs(files=files, manifest=changed)[2])["schema_version"], 1)
        for revision in ["R" * 129, "bad/id", True, None]:
            self.error("fcc_case_invalid_packet", self.inputs(files=files, manifest={**manifest, "revision": revision}))
        changed = deepcopy(manifest); changed["files"] = changed["files"][:1]
        self.error("fcc_case_invalid_packet", self.inputs(files=files, manifest=changed))
        changed = deepcopy(manifest)
        changed["files"] += [{"path": "unconsumed/" + str(i) + ".bin", "bytes": 0, "sha256": "f" * 64} for i in range(126)]
        self.assertEqual(len(self.prepare(files=files, manifest=changed)["provenance"]["consumed_files"]), 2)
        changed["files"].append({"path": "unconsumed/last.bin", "bytes": 0, "sha256": "f" * 64})
        self.error("fcc_case_limit_exceeded", self.inputs(files=files, manifest=changed))

    def test_manifest_flags_and_extra_metadata_do_not_grant_authority(self):
        raw, files, options = self.inputs(); manifest = json.loads(raw)
        self.assertFalse(self.prepare(files=files, manifest={**manifest, "observations": {"current": True, "value": 0}})["verification"]["execution_authorized"])
        for flag in ["source_code_executed", "runtime_or_hardware_support_confirmed", "public_export_allowed"]:
            self.assertEqual(self.prepare(files=files, manifest={**manifest, flag: False})["schema_version"], 1)
            for bad in [True, 0, None, "false"]:
                self.error("fcc_case_invalid_packet", self.inputs(files=files, manifest={**manifest, flag: bad}))
        self.error("fcc_case_invalid_packet", self.inputs(files=files, manifest={**manifest, "request_id": "DEV-CONTROL-SOURCES-008"}))

    def test_manifest_rows_reject_extra_keys_bool_sizes_bad_hashes_and_case_aliases(self):
        raw, files, options = self.inputs(); manifest = json.loads(raw)
        for change in [{"bytes": True}, {"bytes": -1}, {"sha256": "F" * 64}, {"extra": False}]:
            changed = deepcopy(manifest); changed["files"][0].update(change)
            self.error("fcc_case_invalid_packet", self.inputs(files=files, manifest=changed))
        for path in [self.packet_path, self.packet_path.upper()]:
            changed = deepcopy(manifest); changed["files"].append({**changed["files"][0], "path": path})
            self.error("fcc_case_invalid_packet", self.inputs(files=files, manifest=changed))

    def test_lexical_paths_and_selectors_are_explicit_distinct_json_paths(self):
        raw, files, options = self.inputs(); manifest = json.loads(raw)
        for path in ["/absolute.json", "../outside.json", "a\\b.json", "a//b.json", "CON.json", "a:stream.json", "trailing. /x.json", "intake-v1.json"]:
            changed = deepcopy(manifest); changed["files"][0]["path"] = path
            self.error("fcc_case_invalid_packet", self.inputs(files=files, manifest=changed))
        for changes in [{"page_scope_path": self.packet_path}, {"packet_path": None}, {"packet_path": "../packet.json"},
                        {"packet_path": "packet.txt"}, {"page_scope_path": "CON.json"}]:
            self.error("fcc_case_invalid_packet", (raw, files, {**options, **changes}))

    def test_duplicate_keys_invalid_utf8_nonfinite_and_nonobject_json_are_rejected(self):
        raw, files, options = self.inputs()
        for malformed in [b'\xff', b'{}{}', b'[]', b'{"request_id":"x","request_id":"y"}',
                          raw[:-1] + b',"unknown":NaN}', raw[:-1] + b',"unknown":1e99999}']:
            self.error("fcc_case_invalid_packet", (malformed, files, {**options, "expected_manifest_sha256": digest(malformed)}))
        for path in [self.packet_path, self.scope_path]:
            for malformed in [b'null', b'{}', b'{"schema_version":1,"schema_version":1}']:
                self.error("fcc_case_invalid_packet", self.inputs(files={**files, path: malformed}))

    def test_output_evidence_key_and_bad_metadata_reference_are_never_accepted(self):
        for update in [{"literal_verified": True}, {"document_id": "MISSING"}, {"source_sha256": "e" * 64}, {"file_page": True}]:
            packet = deepcopy(self.packet); packet["cases"][0]["claims"][0]["evidence"][0].update(update)
            self.error("fcc_case_invalid_evidence", self.inputs(packet=packet))
        packet = deepcopy(self.packet); packet["cases"][0]["claims"][0]["output_only"] = False
        self.error("fcc_case_invalid_packet", self.inputs(packet=packet))

    def test_scope_is_required_exactly_bound_and_does_not_promote_unselected_evidence(self):
        for policy in [None, {}, {"schema_version": 1, "sources": {}}]:
            self.error("fcc_case_invalid_packet", self.inputs(policy=policy if policy is not None else False))
        for pages in [[], [True], [1, 1], [3]]:
            policy = deepcopy(self.policy); next(iter(policy["sources"].values()))["pages"] = pages
            self.error("fcc_case_invalid_packet", self.inputs(policy=policy))
        policy = deepcopy(self.policy); next(iter(policy["sources"].values()))["pages"] = [2]
        self.error("fcc_case_invalid_evidence", self.inputs(policy=policy))

    def test_packet_and_manifest_and_scope_resource_caps_precede_interpretation(self):
        raw, files, options = self.inputs()
        large = raw + b" " * (1024 * 1024)
        self.error("fcc_case_limit_exceeded", (large, files, {**options, "expected_manifest_sha256": digest(large)}))
        for path, limit in [(self.packet_path, 4 * 1024 * 1024), (self.scope_path, 64 * 1024)]:
            self.error("fcc_case_limit_exceeded", self.inputs(files={**files, path: b" " * (limit + 1)}))
        manifest = json.loads(raw); nested = None
        for _ in range(18): nested = [nested]
        self.error("fcc_case_limit_exceeded", self.inputs(files=files, manifest={**manifest, "ignored": nested}))
        self.error("fcc_case_limit_exceeded", self.inputs(files=files, manifest={**manifest, "ignored": [0] * 50001}))

    def test_exact_raw_byte_caps_are_accepted_and_return_budget_is_enforced(self):
        raw, files, options = self.inputs()
        files = {path: blob + b" " * (limit - len(blob)) for path, blob, limit in [
            (self.packet_path, files[self.packet_path], 4 * 1024 * 1024),
            (self.scope_path, files[self.scope_path], 64 * 1024)]}
        raw, files, options = self.inputs(files=files)
        raw += b" " * (1024 * 1024 - len(raw)); options["expected_manifest_sha256"] = digest(raw)
        self.assertEqual(cases.prepare_fcc_case_packet(raw, files, **options)["kind"], "fcc_case_packet_preparation")
        with mock.patch.object(cases, "_OUTPUT_BYTES", 1):
            self.error("fcc_case_limit_exceeded")

    def test_declaration_only_pdf_limits_and_total_source_budget_are_enforced(self):
        packet = deepcopy(self.packet); packet["documents"][0]["size_bytes"] = 16 * 1024 * 1024 + 1
        self.error("fcc_case_limit_exceeded", self.inputs(packet=packet))
        packet = deepcopy(self.packet); policy = deepcopy(self.policy)
        for index in range(1, 5):
            document = deepcopy(packet["documents"][0]); document.update(document_id="DOC-" + str(index), sha256=digest(str(index).encode()))
            packet["documents"].append(document); policy["sources"][document["sha256"]] = deepcopy(next(iter(policy["sources"].values())))
        for document in packet["documents"]: document["size_bytes"] = 16 * 1024 * 1024
        self.error("fcc_case_limit_exceeded", self.inputs(packet=packet, policy=policy))

    def test_source16_total64mib_and_selection800_normal_upper_input_needs_no_pdf(self):
        packet = deepcopy(self.packet); policy = deepcopy(self.policy)
        for index in range(1, 16):
            document = deepcopy(packet["documents"][0]); document.update(document_id="DOC-" + str(index), sha256=digest(str(index).encode()))
            packet["documents"].append(document)
            policy["sources"][document["sha256"]] = deepcopy(next(iter(policy["sources"].values())))
        for document in packet["documents"]:
            document.update(size_bytes=4 * 1024 * 1024, physical_pages=50)
            policy["sources"][document["sha256"]]["pages"] = list(range(50, 0, -1))
        result = self.prepare(packet=packet, policy=policy)
        self.assertEqual(len(result["source_refs"]), 16)
        self.assertEqual(sum(len(s["pages"]) for s in result["page_scope"]["sources"].values()), 800)
        self.assertEqual([r["document_id"] for r in result["source_refs"]], sorted(r["document_id"] for r in result["source_refs"]))

    def test_source200_pages_and_total800_accept_exact_boundary_then_reject801(self):
        packet = deepcopy(self.packet); policy = deepcopy(self.policy)
        for index in range(1, 4):
            document = deepcopy(packet["documents"][0]); document.update(document_id="DOC-" + str(index), sha256=digest(str(index).encode()))
            packet["documents"].append(document); policy["sources"][document["sha256"]] = deepcopy(next(iter(policy["sources"].values())))
        for document in packet["documents"]:
            document["physical_pages"] = 200
            policy["sources"][document["sha256"]]["pages"] = list(range(1, 201))
        self.assertEqual(sum(len(r["pages"]) for r in self.prepare(packet=packet, policy=policy)["page_scope"]["sources"].values()), 800)
        document = deepcopy(packet["documents"][0]); document.update(document_id="LAST", sha256="f" * 64)
        packet["documents"].append(document); policy["sources"][document["sha256"]] = {**deepcopy(next(iter(policy["sources"].values()))), "pages": [1]}
        self.error("fcc_case_limit_exceeded", self.inputs(packet=packet, policy=policy))

    def test_declared_physical_page100000_is_not_an_actual_count_assertion(self):
        packet = deepcopy(self.packet); packet["documents"][0]["physical_pages"] = 100000
        result = self.prepare(packet=packet)
        self.assertEqual(result["source_refs"][0]["physical_pages"], 100000)
        self.assertFalse(result["verification"]["source_pdf_bytes_verified"])
        packet["documents"][0]["physical_pages"] = 100001
        self.error("fcc_case_invalid_packet", self.inputs(packet=packet))

    def test_canonical_input_output_are_detached_and_arrays_ordinary_values_preserved(self):
        packet = deepcopy(self.packet); packet["cases"][0]["claims"].reverse()
        packet["scope"]["search_scope_notes"] = [" same ", " same "]
        packet["cases"][0]["claims"][0]["value"] = [0, 0.0, False, None, " spaced "]
        raw, files, options = self.inputs(packet=packet)
        before = deepcopy(files); result = cases.prepare_fcc_case_packet(raw, files, **options)
        self.assertEqual(result["packet"], packet)
        self.assertEqual(files, before)
        result["packet"]["cases"][0]["claims"].clear(); result["page_scope"]["sources"].clear()
        self.assertEqual(cases.prepare_fcc_case_packet(raw, files, **options)["packet"], packet)
        files.clear(); self.assertEqual(packet["scope"]["search_scope_notes"], [" same ", " same "])

    def test_object_key_order_changes_canonical_hash_not_array_semantics(self):
        first = self.prepare()
        packet = dict(reversed(list(self.packet.items())))
        policy = dict(reversed(list(self.policy.items())))
        second = self.prepare(packet=packet, policy=policy)
        self.assertEqual(first["provenance"]["packet_sha256"], second["provenance"]["packet_sha256"])
        self.assertEqual(first["provenance"]["page_scope_sha256"], second["provenance"]["page_scope_sha256"])
        self.assertEqual(list(second["packet"]), sorted(second["packet"]))

    def test_empty_corpus_still_requires_two_pinned_metadata_files(self):
        packet = deepcopy(self.packet); packet.update(documents=[], cases=[])
        result = self.prepare(packet=packet, policy={"schema_version": 1, "sources": {}})
        self.assertEqual(result["source_refs"], []); self.assertEqual(result["packet"]["cases"], [])
        self.assertFalse(result["verification"]["retained_literals_verified"])


class FccReportPageScopeTests(unittest.TestCase):
    """030 selected-source contract, using synthetic original bytes only."""

    def setUp(self):
        self.assertIn("page_scope", inspect.signature(cases.FccReportCaseCatalog).parameters,
                      "030 optional page_scope is absent")
        self.packet, self.sources, _ = fixture()
        first = extract_document(next(iter(self.sources.values())), "DOC-A.pdf")["pages"][0]["text"]
        self.replace(synthetic_pdf([first, "UNSELECTED SYNTHETIC MARKER", "SELECTED THIRD PAGE"]), 3)

    def replace(self, payload, pages):
        document = self.packet["documents"][0]
        document.update(sha256=digest(payload), size_bytes=len(payload), physical_pages=pages)
        self.sources = {document["sha256"]: payload}
        for case in self.packet["cases"]:
            for claim in case["claims"]:
                for evidence in claim["evidence"]:
                    evidence["source_sha256"] = document["sha256"]

    def scope(self, pages=(1,), mode="native_text"):
        return {"schema_version": 1, "sources": {sha: {"pages": list(pages), "mode": mode,
                "basis_id": "SYNTHETIC-SCOPE-030", "basis_sha256": "d" * 64} for sha in self.sources}}

    def catalog(self, policy=None):
        return cases.FccReportCaseCatalog(self.packet, self.sources, page_scope=policy or self.scope())

    def error(self, code, policy, packet=None, sources=None):
        with self.assertRaises(cases.FccReportCaseError) as caught:
            cases.FccReportCaseCatalog(packet or self.packet, sources or self.sources, page_scope=policy)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.args, (code,))
        self.assertIsNone(caught.exception.__context__)

    def encrypted(self, permissions, user="", owner="SYNTHETIC-OWNER"):
        writer = PdfWriter(); writer.append(PdfReader(BytesIO(next(iter(self.sources.values())))))
        writer.encrypt(user, owner_password=owner, permissions_flag=permissions)
        stream = BytesIO(); writer.write(stream); writer.close()
        return stream.getvalue()

    def test_none_replays_existing_public_interfaces_and_from_json(self):
        plain = cases.FccReportCaseCatalog(self.packet, self.sources)
        explicit = cases.FccReportCaseCatalog(self.packet, self.sources, page_scope=None)
        decoded = cases.FccReportCaseCatalog.from_json(json.dumps(self.packet), self.sources, page_scope=None)
        self.assertEqual(plain.summary(), explicit.summary())
        self.assertEqual(plain.case("CASE-A"), decoded.case("CASE-A"))
        query = {"product_family": "sensor_node", "rule": "47 CFR 15.247", "method": "ANSI C63.10-2020", "model": "MODEL-A"}
        self.assertEqual(plain.search(query), explicit.search(query))
        self.assertEqual(plain.discover(query), explicit.discover(query))

    def test_noncontiguous_pages_keep_original_numbers_and_partial_diagnostics(self):
        policy = self.scope((3, 1)); before = deepcopy(policy)
        result = self.catalog(policy).case("CASE-A")
        doc = result["documents"][0]
        self.assertEqual(policy, before)
        self.assertEqual([page["file_page"] for page in doc["page_index"]], [1, 3])
        self.assertEqual(doc["extraction"]["total_pages"], 3)
        self.assertEqual(doc["extraction"]["processed_pages"], 2)
        self.assertEqual(doc["extraction"]["status"], "partial")
        self.assertFalse(doc["extraction"]["complete"])
        self.assertEqual(doc["extraction"]["parser"]["name"], "pypdf-selected-pages")
        issues = doc["extraction"]["issues"]
        self.assertIn({"code": "page_scope_applied", "file_page": None}, issues)
        self.assertIn({"code": "page_scope_native_text", "file_page": None}, issues)
        self.assertIn({"code": "page_scope_outside_unprocessed", "file_page": None}, issues)
        self.assertEqual([r["file_page"] for r in issues if r["code"] == "page_scope_requested"], [1, 3])
        self.assertTrue(all(page["citable"] for page in doc["page_index"]))
        self.assertEqual(set(result), COMMON | {"case", "documents"})

    def test_content_and_text_calls_visit_only_selected_pages_without_legacy_filtering(self):
        content_calls, text_calls = [], []
        content, text = PageObject.get_contents, PageObject.extract_text
        def selected_content(page, *args, **kwargs):
            content_calls.append(page.pdf.get_page_number(page) + 1)
            return content(page, *args, **kwargs)
        def selected_text(page, *args, **kwargs):
            text_calls.append(page.pdf.get_page_number(page) + 1)
            return text(page, *args, **kwargs)
        with mock.patch.object(PageObject, "get_contents", new=selected_content), \
                mock.patch.object(PageObject, "extract_text", new=selected_text), \
                mock.patch.object(cases, "extract_document", side_effect=AssertionError("full read")), \
                mock.patch.object(cases, "_public_read_pdf", side_effect=AssertionError("legacy public read")):
            self.catalog(self.scope((3, 1)))
        self.assertEqual(text_calls, [1, 3])
        self.assertEqual(set(content_calls), {1, 3})

    def test_evidence_outside_selection_is_rejected_without_native_processing(self):
        with mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("native read")) as called:
            self.error("fcc_case_invalid_evidence", self.scope((2,)))
        called.assert_not_called()

    def test_bad_policy_source_and_page_shapes_fail_before_native_processing(self):
        policies = [False, {}, {"schema_version": True, "sources": {}}, {"schema_version": 1, "sources": {}},
                    {"schema_version": 1, "sources": {"0" * 64: next(iter(self.scope()["sources"].values()))}}]
        for changes in ({"pages": []}, {"pages": [1, 1]}, {"pages": [True]}, {"pages": [0]}, {"pages": [4]},
                        {"mode": "print"}, {"basis_id": "C:/not-a-basis"}, {"basis_sha256": "D" * 64}, {"approval": True}):
            policy = self.scope(); next(iter(policy["sources"].values())).update(changes); policies.append(policy)
        for policy in policies:
            with self.subTest(policy_type=type(policy).__name__), \
                    mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("native read")) as called:
                self.error("fcc_case_invalid_packet", policy)
                called.assert_not_called()

    def test_policy_bytes_depth_nodes_and_page_limits_are_preflight_limits(self):
        policies = [self.scope(tuple(range(1, 202))), {"extra": ["x" * 100] * 800}, {"extra": [0] * 4100}]
        nested = None
        for _ in range(9): nested = [nested]
        policies.append({"extra": nested})
        for policy in policies:
            with self.subTest(kind=list(policy)), mock.patch("pypdf.PdfReader", side_effect=AssertionError("reader opened")) as reader:
                self.error("fcc_case_limit_exceeded", policy)
                reader.assert_not_called()

    def test_global_requested_page_budget_is_checked_before_opening_sources(self):
        packet = deepcopy(self.packet); packet.update(documents=[], cases=[]); sources = {}; scope = {"schema_version": 1, "sources": {}}
        for i in range(5):
            payload = b"%PDF-1.7\nSYNTHETIC-" + str(i).encode(); sha = digest(payload)
            doc = deepcopy(self.packet["documents"][0]); doc.update(document_id="DOC-" + str(i), sha256=sha, size_bytes=len(payload), physical_pages=200)
            packet["documents"].append(doc); sources[sha] = payload
            scope["sources"][sha] = {"pages": list(range(1, 201)), "mode": "native_text", "basis_id": "SYNTHETIC-030", "basis_sha256": "d" * 64}
        with mock.patch("pypdf.PdfReader", side_effect=AssertionError("reader opened")) as reader:
            self.error("fcc_case_limit_exceeded", scope, packet, sources)
        reader.assert_not_called()

    def test_all_source_count_metadata_is_verified_before_first_native_operation(self):
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
        writer._pages.get_object()[NameObject("/Count")] = NumberObject(2)
        stream = BytesIO(); writer.write(stream); writer.close(); payload = stream.getvalue(); sha = digest(payload)
        doc = deepcopy(self.packet["documents"][0]); doc.update(document_id="BAD-COUNT", sha256=sha, size_bytes=len(payload), physical_pages=2)
        self.packet["documents"].append(doc); self.sources[sha] = payload
        with mock.patch.object(PageObject, "get_contents", side_effect=AssertionError("native content before all-source count")) as content, \
                mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("native text")) as text:
            self.error("fcc_case_pdf_invalid", self.scope())
        content.assert_not_called(); text.assert_not_called()

    def test_nested_pages_count_mismatch_is_not_hidden_by_correct_root_count(self):
        writer = PdfWriter(); writer.append(PdfReader(BytesIO(next(iter(self.sources.values())))), pages=(0, 1))
        root = writer._pages.get_object(); leaf_ref = root["/Kids"][0]
        child = DictionaryObject({NameObject("/Type"): NameObject("/Pages"), NameObject("/Count"): NumberObject(2),
                                  NameObject("/Kids"): ArrayObject([leaf_ref]), NameObject("/Parent"): writer._pages})
        child_ref = writer._add_object(child); root[NameObject("/Kids")] = ArrayObject([child_ref]); root[NameObject("/Count")] = NumberObject(1)
        leaf_ref.get_object()[NameObject("/Parent")] = child_ref
        stream = BytesIO(); writer.write(stream); writer.close(); self.replace(stream.getvalue(), 1)
        with mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("native text")) as text:
            self.error("fcc_case_pdf_invalid", self.scope())
        text.assert_not_called()

    def test_accessibility_preserves_copy_false_and_does_not_authorize_native_mode(self):
        permissions = UserAccessPermissions.PRINT | UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
        payload = self.encrypted(permissions); self.replace(payload, 3); before = digest(payload)
        result = self.catalog(self.scope(mode="accessibility")).case("CASE-A")
        self.assertEqual(result["documents"][0]["extraction"]["parser"]["name"],
                         "pypdf-public-empty-user-password-accessibility-selected-pages")
        self.assertEqual([p["file_page"] for p in result["documents"][0]["page_index"]], [1])
        self.assertEqual(digest(payload), before)
        self.assertFalse(result["documents"][0]["rights"]["public_redistribution_allowed"])
        self.error("fcc_case_extraction_unavailable", self.scope(mode="native_text"))
        self.assertEqual(extract_document(payload, "synthetic.pdf")["status"], "encrypted")

    def test_encrypted_native_mode_reads_once_only_with_copy_flag(self):
        from pypdf._encryption import Encryption
        self.replace(self.encrypted(UserAccessPermissions.EXTRACT), 3)
        original, attempts = Encryption.verify, []
        def verify(encryption, password, **kwargs):
            attempts.append(password); return original(encryption, password, **kwargs)
        with mock.patch.object(Encryption, "verify", new=verify), \
                mock.patch.object(PdfReader, "decrypt", side_effect=AssertionError("retry")), \
                mock.patch.object(PdfWriter, "write", side_effect=AssertionError("PDF rewrite")):
            result = self.catalog().summary()
        self.assertEqual(attempts, [""])
        self.assertEqual(result["documents"][0]["extraction"]["parser"]["name"], "pypdf-public-empty-user-password-selected-pages")

    def test_print_only_and_unknown_permission_integrity_do_not_allow_content(self):
        self.replace(self.encrypted(UserAccessPermissions.PRINT), 3)
        for mode in ("native_text", "accessibility"):
            with mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("native text")) as text:
                self.error("fcc_case_extraction_unavailable", self.scope(mode=mode))
            text.assert_not_called()
        for known in (None, False):
            with mock.patch.object(PdfReader, "are_permissions_valid", new_callable=mock.PropertyMock, return_value=known), \
                    mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("native text")) as text:
                self.error("fcc_case_extraction_unavailable", self.scope())
            text.assert_not_called()

    def test_all_source_permission_preflight_precedes_first_native_read(self):
        payload = self.encrypted(UserAccessPermissions.PRINT); sha = digest(payload)
        doc = deepcopy(self.packet["documents"][0]); doc.update(document_id="NO-COPY", sha256=sha, size_bytes=len(payload))
        self.packet["documents"].append(doc); self.sources[sha] = payload
        with mock.patch.object(PageObject, "get_contents", side_effect=AssertionError("content before permission preflight")) as content:
            self.error("fcc_case_extraction_unavailable", self.scope())
        content.assert_not_called()

    def test_secret_owner_only_and_existing_user_encryption_remain_rejected(self):
        packet, sources = deepcopy(self.packet), self.sources.copy()
        for user, owner, kind in (("SECRET", "OWNER", "mirror"), ("SECRET", "", "mirror"), ("", "OWNER", "existing_user")):
            self.packet, self.sources = deepcopy(packet), sources.copy()
            self.replace(self.encrypted(UserAccessPermissions.all(), user=user, owner=owner), 3)
            self.packet["documents"][0]["exhibits"][0]["source_kind"] = kind
            self.error("fcc_case_pdf_invalid", self.scope())

    def test_page_hash_quotes_detached_scope_and_output_keep_original_source(self):
        policy = self.scope((1,)); original = deepcopy(policy); catalog = self.catalog(policy)
        before = catalog.case("CASE-A")
        next(iter(policy["sources"].values()))["pages"][:] = [2]
        self.packet["cases"][0]["claims"][0]["value"] = "changed input"
        result = catalog.case("CASE-A"); result["documents"][0]["page_index"].clear()
        self.assertEqual(catalog.case("CASE-A"), before)
        evidence = before["case"]["claims"][0]["evidence"][0]
        self.assertTrue(evidence["literal_verified"])
        self.assertEqual(evidence["quote"], "SYNTHETIC REPORT: SYN-001")
        self.assertEqual(evidence["source_sha256"], next(iter(self.sources)))
        decoded = cases.FccReportCaseCatalog.from_json(json.dumps(fixture()[0]), fixture()[1],
            page_scope={"schema_version": 1, "sources": {sha: {**next(iter(original["sources"].values())), "pages": [1]}
                                                        for sha in fixture()[1]}})
        self.assertEqual(decoded.case("CASE-A")["case"]["claims"][0]["evidence"][0]["quote"], evidence["quote"])

    def test_selected_empty_image_warning_and_limits_do_not_create_false_citations(self):
        first = extract_document(next(iter(self.sources.values())), "DOC-A.pdf")["pages"][0]["text"]
        self.replace(synthetic_pdf([first, None, "THIRD"], images={1}), 3)
        self.packet["cases"][0]["claims"] = []
        result = self.catalog(self.scope((2,))).summary()
        page = result["documents"][0]["page_index"][0]
        self.assertEqual(page["status"], "image_only"); self.assertFalse(page["citable"])
        self.assertEqual(result["documents"][0]["extraction"]["status"], "partial")
        self.assertEqual(result["counts"]["no_citable_text_pdfs"], 1)
        self.packet, self.sources, _ = fixture()
        with mock.patch.object(cases._extract, "_warnings_observable", return_value=False):
            self.error("fcc_case_invalid_evidence", self.scope())

    def test_empty_corpus_accepts_empty_policy_without_pretending_page_success(self):
        self.packet.update(documents=[], cases=[]); self.sources.clear()
        result = cases.FccReportCaseCatalog(self.packet, self.sources, page_scope={"schema_version": 1, "sources": {}}).summary()
        self.assertEqual(result["documents"], []); self.assertEqual(result["counts"]["parsed_unique_pdfs"], 0)

    def test_indirect_kids_and_count_are_valid_page_tree_metadata(self):
        writer = PdfWriter(); writer.append(PdfReader(BytesIO(next(iter(self.sources.values())))))
        root = writer._pages.get_object()
        root[NameObject("/Kids")] = writer._add_object(root["/Kids"])
        root[NameObject("/Count")] = writer._add_object(NumberObject(3))
        stream = BytesIO(); writer.write(stream); writer.close(); self.replace(stream.getvalue(), 3)
        self.assertEqual(self.catalog().summary()["documents"][0]["extraction"]["processed_pages"], 1)

    def test_missing_authentication_or_permission_interfaces_fail_unavailable(self):
        self.replace(self.encrypted(UserAccessPermissions.EXTRACT), 3)
        from pypdf._encryption import Encryption
        original = Encryption.verify
        def missing_authentication(encryption, password, **kwargs):
            result = original(encryption, password, **kwargs)
            del encryption._password_type
            return result
        with mock.patch.object(Encryption, "verify", new=missing_authentication), \
                mock.patch.object(PageObject, "get_contents", side_effect=AssertionError("content read")) as content:
            self.error("fcc_case_extraction_unavailable", self.scope())
        content.assert_not_called()
        with mock.patch.object(PdfReader, "are_permissions_valid", new_callable=mock.PropertyMock,
                               side_effect=AttributeError("unsupported property")), \
                mock.patch.object(PageObject, "extract_text", side_effect=AssertionError("text read")) as text:
            self.error("fcc_case_extraction_unavailable", self.scope())
        text.assert_not_called()

    def test_selected_failures_limits_and_full_scope_preserve_real_page_statuses(self):
        self.packet["cases"][0]["claims"] = []
        all_pages = self.catalog(self.scope((1, 2, 3))).summary()["documents"][0]
        self.assertEqual(all_pages["extraction"]["status"], "ok"); self.assertTrue(all_pages["extraction"]["complete"])
        self.assertNotIn("page_scope_outside_unprocessed", {issue["code"] for issue in all_pages["extraction"]["issues"]})
        with mock.patch.object(cases._extract, "_inspect_content", side_effect=cases._extract._ContentLimit()):
            doc = self.catalog(self.scope((3,))).summary()["documents"][0]
        self.assertEqual(doc["page_index"][0]["status"], "limit_exceeded"); self.assertFalse(doc["page_index"][0]["citable"])
        with mock.patch.object(PageObject, "extract_text", side_effect=ValueError("synthetic malformed text")):
            doc = self.catalog(self.scope((2,))).summary()["documents"][0]
        self.assertEqual(doc["page_index"][0]["status"], "error"); self.assertEqual(doc["extraction"]["processed_pages"], 1)
        with mock.patch.object(PageObject, "extract_text", return_value="X" * 1000001) as text:
            doc = self.catalog(self.scope((1, 3))).summary()["documents"][0]
        self.assertEqual(text.call_count, 1)
        self.assertEqual([p["file_page"] for p in doc["page_index"]], [1])
        self.assertEqual(doc["page_index"][0]["status"], "truncated"); self.assertFalse(doc["page_index"][0]["citable"])
        self.assertIn({"code": "page_scope_requested", "file_page": 3}, doc["extraction"]["issues"])

    def test_late_preflight_failure_closes_all_open_readers_without_content(self):
        payload = self.encrypted(UserAccessPermissions.PRINT); sha = digest(payload)
        doc = deepcopy(self.packet["documents"][0]); doc.update(document_id="DENIED", sha256=sha, size_bytes=len(payload))
        self.packet["documents"].append(doc); self.sources[sha] = payload
        closed, close = [], PdfReader.close
        def tracked_close(reader):
            stream = reader.stream
            close(reader); closed.append(stream)
        with mock.patch.object(PdfReader, "close", new=tracked_close), \
                mock.patch.object(PageObject, "get_contents", side_effect=AssertionError("native content")) as content:
            self.error("fcc_case_extraction_unavailable", self.scope())
        content.assert_not_called(); self.assertEqual(len(closed), 2)
        self.assertTrue(all(stream.closed for stream in closed))

    def test_different_source_selections_keep_separate_warning_locations(self):
        payload = synthetic_pdf(["OTHER SOURCE FIRST", "OTHER SOURCE SECOND"]); sha = digest(payload)
        doc = deepcopy(self.packet["documents"][0]); doc.update(document_id="OTHER", sha256=sha, size_bytes=len(payload), physical_pages=2)
        self.packet["documents"].append(doc); self.sources[sha] = payload
        self.packet["cases"][0]["document_ids"].append("OTHER")
        policy = self.scope(); policy["sources"][sha]["pages"] = [2]
        original = PageObject.extract_text
        def warned_text(page, *args, **kwargs):
            result = original(page, *args, **kwargs)
            if result.startswith("OTHER"):
                logging.getLogger("pypdf").warning("synthetic selected warning")
            return result
        with mock.patch.object(PageObject, "extract_text", new=warned_text):
            docs = self.catalog(policy).case("CASE-A")["documents"]
        self.assertTrue(docs[0]["page_index"][0]["citable"])
        self.assertFalse(docs[1]["page_index"][0]["citable"])
        self.assertIn({"code": "parser_warning", "file_page": 2}, docs[1]["extraction"]["issues"])


if __name__ == "__main__":
    unittest.main()

"""Synthetic report cases; no collected source, customer value, or actual AI."""

from copy import deepcopy
import hashlib
from io import BytesIO
import json
import math
import unittest
from unittest import mock

from pypdf import PdfReader, PdfWriter

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


if __name__ == "__main__":
    unittest.main()

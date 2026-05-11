import json

from llm_code_validator.signatures import load_signatures, validate_signature_database


def _write_db(path, rule):
    path.write_text(
        json.dumps({"demo": {"current_version": "1.x", "methods": {"old_api": rule}}}),
        encoding="utf-8",
    )


def test_validate_signature_database_accepts_valid_rule(tmp_path):
    db = tmp_path / "library_signatures.json"
    _write_db(
        db,
        {
            "exists": False,
            "removed_in": "1.0.0",
            "reason": "removed",
            "replacement": "new_api",
            "source_note": "official docs",
        },
    )
    assert validate_signature_database(str(db)) == []


def test_validate_signature_database_rejects_missing_methods(tmp_path):
    db = tmp_path / "library_signatures.json"
    db.write_text(json.dumps({"demo": {}}), encoding="utf-8")
    assert validate_signature_database(str(db))


def test_validate_signature_database_rejects_safe_fix_without_replacement(tmp_path):
    db = tmp_path / "library_signatures.json"
    _write_db(db, {"exists": False, "removed_in": "1.0.0", "reason": "removed", "fix_safety": "safe_fix"})
    errors = validate_signature_database(str(db))
    assert any("safe_fix requires replacement" in error for error in errors)


def test_validate_signature_database_rejects_missing_evidence(tmp_path):
    db = tmp_path / "library_signatures.json"
    _write_db(db, {"exists": False, "removed_in": "1.0.0", "reason": "removed"})
    errors = validate_signature_database(str(db))
    assert any("missing evidence" in error for error in errors)


def test_validate_signature_database_rejects_generic_evidence_when_strict(tmp_path):
    db = tmp_path / "library_signatures.json"
    _write_db(db, {"exists": False, "removed_in": "1.0.0", "reason": "removed", "source_note": "generic"})
    errors = validate_signature_database(str(db), require_official_evidence=True)
    assert any("source_url or release_note" in error for error in errors)


def test_at_least_top_20_rules_have_official_evidence():
    rules = load_signatures()
    official_count = sum(
        1
        for library_rules in rules.values()
        for rule in library_rules
        if rule.evidence.startswith("http")
    )
    assert official_count >= 20


def test_safe_fix_rule_count_is_product_useful():
    rules = load_signatures()
    safe_count = sum(1 for library_rules in rules.values() for rule in library_rules if rule.fix_safety == "safe_fix")
    assert safe_count >= 10


def test_load_signatures_normalizes_rules(tmp_path):
    db = tmp_path / "library_signatures.json"
    _write_db(
        db,
        {
            "exists": False,
            "removed_in": "1.0.0",
            "reason": "removed",
            "replacement": "new_api",
            "source_note": "official docs",
        },
    )
    rules = load_signatures(str(db))
    assert rules["demo"][0].symbol == "old_api"
    assert rules["demo"][0].fix_safety == "suggested_fix"

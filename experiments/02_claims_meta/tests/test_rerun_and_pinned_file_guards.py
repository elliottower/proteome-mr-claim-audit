import hashlib
import json

import pytest

import apply_eligibility
import build_registry
import run_extraction


def test_apply_eligibility_refuses_to_replace_its_decisions_file(tmp_path, monkeypatch):
    rows = tmp_path / "sol_eligibility_search_abc.jsonl"
    rows.write_text(json.dumps({"pmid": "1", "status": "extraction_failed", "output": None}) + "\n")
    monkeypatch.setattr("sys.argv", ["apply_eligibility.py", "--eligibility", str(rows)])
    apply_eligibility.main()
    out = tmp_path / "sol_eligibility_search_abc.decisions.jsonl"
    first = out.read_text()
    assert json.loads(first) == {"pmid": "1", "decision": "extraction_failed", "reasons": [],
                                 "flags": [], "n_proteins_tested": None, "count_other": None}
    rows.write_text("")
    with pytest.raises(FileExistsError, match="archive it"):
        apply_eligibility.main()
    assert out.read_text() == first


def test_run_extraction_refuses_a_label_whose_parsed_file_exists_before_any_request(
        tmp_path, monkeypatch):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "eligibility_prompt.md").write_text("Decide.")
    (prompts / "schema.json").write_text(json.dumps({"eligibility": {"type": "object"}}))
    abstracts = tmp_path / "abstracts.jsonl"
    abstracts.write_text(json.dumps({"pmid": "1", "title": "t", "abstract": "a"}) + "\n")
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    rev = run_extraction.revision_id("eligibility", "Decide.", {"type": "object"})
    existing = parsed / f"sol_eligibility_search_{rev}.jsonl"
    existing.write_text("kept\n")
    requests = []
    monkeypatch.setattr(run_extraction, "PROMPTS", prompts)
    monkeypatch.setattr(run_extraction, "PARSED", parsed)
    monkeypatch.setattr(run_extraction, "run_one", lambda *args: requests.append(args))
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-key")
    monkeypatch.setattr("sys.argv", [
        "run_extraction.py", "--task", "eligibility", "--label", "search", "--abstracts",
        str(abstracts), "--raw-root", str(tmp_path / "raw")])
    with pytest.raises(run_extraction.ExtractionRunError, match="exists; archive it"):
        run_extraction.main()
    assert requests == []
    assert existing.read_text() == "kept\n"
    assert not (tmp_path / "raw").exists()


def test_pinned_file_is_returned_only_for_the_bytes_the_manifest_names(tmp_path):
    held = tmp_path / "inputs" / "hgnc.tsv"
    held.parent.mkdir()
    held.write_bytes(b"hgnc_id\tstatus\n")
    spec = {"file": "inputs/hgnc.tsv", "sha256": hashlib.sha256(b"hgnc_id\tstatus\n").hexdigest()}
    assert build_registry.pinned_file(spec, tmp_path) == held
    held.write_bytes(b"hgnc_id\tstatus\r\n")
    with pytest.raises(build_registry.PinnedFileError, match="differs from reference/MANIFEST"):
        build_registry.pinned_file(spec, tmp_path)
    held.unlink()
    with pytest.raises(build_registry.PinnedFileError, match="inputs/hgnc.tsv missing"):
        build_registry.pinned_file(spec, tmp_path)

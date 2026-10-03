import hashlib

import pytest

import verify_spans as vs


def test_record_without_a_recorded_digest_is_accepted_and_a_wrong_digest_raises():
    text = "IL6R lowered CAD risk."
    digest = hashlib.sha256(text.encode()).hexdigest()
    vs.check_digest({"pmid": "1", "abstract": text}, "abstract", digest, "screening_set.jsonl")
    vs.check_digest({"pmid": "1", "abstract": text, "abstract_sha256": digest}, "abstract",
                    digest, "dev_abstracts.jsonl")
    with pytest.raises(vs.SpanCheckError, match="digest differs"):
        vs.check_digest({"pmid": "1", "abstract": text, "abstract_sha256": "0" * 64},
                        "abstract", digest, "dev_abstracts.jsonl")
    with pytest.raises(vs.SpanCheckError, match="digest differs"):
        vs.check_digest({"pmid": "1", "body": text, "body_sha256": "0" * 64}, "body", digest,
                        "fulltext_bodies.jsonl")


@pytest.mark.parametrize("record_id, url", [
    ("29875488", "https://pubmed.ncbi.nlm.nih.gov/29875488/"),
    ("W2901567682", "https://openalex.org/W2901567682"),
    ("PPR12345", "https://europepmc.org/article/PPR/PPR12345"),
    ("AGR:IND1", None)])
def test_landing_page_follows_the_kind_of_record_id(record_id, url):
    assert vs.record_url(record_id) == url


def test_registered_quote_check_folds_whitespace_and_case_only():
    abstract = vs.fold("Higher  IL6R levels\nlowered CAD risk (OR 0.90).")
    assert vs.fold("higher il6r levels lowered CAD risk") in abstract
    assert vs.fold("higher IL6R levels, lowered CAD risk") not in abstract


def test_stored_cli_output_names_paths_relative_to_the_experiment_folder(tmp_path):
    text = f"claims  {tmp_path}/outputs/citations/x/claims\n\nall found.\n"
    assert vs.relative_paths(text, tmp_path) == "claims  outputs/citations/x/claims\n\nall found.\n"
    assert vs.relative_paths("no path here", tmp_path) == "no path here"
    assert str(vs.EXP) not in vs.relative_paths(f"claims  {vs.EXP}/outputs/c/claims")

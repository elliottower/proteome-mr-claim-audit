import json
import pathlib

import jsonschema
import pytest

PROMPTS = pathlib.Path(__file__).resolve().parent.parent / "prompts"
MODEL = json.loads((PROMPTS / "output_schema.json").read_text())
FINAL = json.loads((PROMPTS / "final_data_schema.json").read_text())
MODEL_REASONS = ["release_not_identified", "conflicting_identifiers",
                 "dataset_absent_from_dictionary", "attribution_unresolved"]
PIPELINE_REASONS = ["no_source", "source_unreadable", "version_not_linked"]


def answer(reasons):
    return {"record_id": "r1", "rows": [{
        "row_id": "outcome_1", "identified_releases": [], "roles": [], "ancestry": [],
        "attribution_state": "explicit", "unresolved_reasons": reasons, "decisive_evidence": [],
        "count_evidence": [], "abstract_transition": "none", "attribution_passage": None,
        "note": "synthetic"}]}


@pytest.mark.parametrize("reason", MODEL_REASONS)
def test_a_model_reason_fits_both_schemas(reason):
    jsonschema.validate(answer([reason]), MODEL)
    jsonschema.validate(answer([reason]), FINAL)


@pytest.mark.parametrize("reason", PIPELINE_REASONS)
def test_a_pipeline_only_reason_fits_the_final_schema_and_not_the_model_schema(reason):
    jsonschema.validate(answer(["attribution_unresolved", reason]), FINAL)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(answer([reason]), MODEL)


def test_an_unknown_reason_fits_neither():
    for schema in (MODEL, FINAL):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(answer(["made_up"]), schema)


def test_the_final_schema_differs_from_the_model_schema_only_in_the_reasons():
    final = json.loads(json.dumps(FINAL))
    for key in ("$comment", "title"):
        final.pop(key)
    reasons = final["properties"]["rows"]["items"]["properties"].pop("unresolved_reasons")
    model = json.loads(json.dumps(MODEL))
    model["properties"]["rows"]["items"]["properties"].pop("unresolved_reasons")
    assert final == model
    assert reasons["items"]["enum"] == MODEL_REASONS + PIPELINE_REASONS

# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic==1.13.0", "httpx==0.28.1", "jsonschema==4.26.0"]
# ///
"""Third version of the two-judge runner (scripts/judge_v2.py, sealed, unchanged and imported).
One change, for the request to Anthropic only: the keywords Anthropic's structured output does
not accept (UNSUPPORTED: numerical and string-length constraints) are removed from the schema
sent with the request (`transport_schema`). Every answer is still validated locally against the
full frozen prompts/judge_schema.json, so a confidence outside 0 to 1 fails validation and counts
as an attempt. The frozen prompt and schema files, the routing, the calibration and the seeds are
unchanged (PREREG.log, 2026-10-14).

The Claude Fable 5.1 requests of the first two-judge run, refused before generation with HTTP 400
for the unsupported keywords, are not attempts: the third version stores its Fable exchanges
apart (`STORE_SUFFIX`), so they are sent again; GPT-6 Astra's stored answers stand and are not
sent again.
"""

import judge_v2 as j2

UNSUPPORTED = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
               "minLength", "maxLength")
STORE_SUFFIX = "_v3"


def transport_schema(schema):
    if isinstance(schema, dict):
        return {k: transport_schema(v) for k, v in schema.items() if k not in UNSUPPORTED}
    if isinstance(schema, list):
        return [transport_schema(v) for v in schema]
    return schema


def removed_keywords(schema, path="") -> list[str]:
    out = []
    if isinstance(schema, dict):
        for k, v in schema.items():
            if k in UNSUPPORTED:
                out.append(f"{path}/{k}")
            out += removed_keywords(v, f"{path}/{k}")
    elif isinstance(schema, list):
        for i, v in enumerate(schema):
            out += removed_keywords(v, f"{path}/{i}")
    return out


def fable_body(system: str, schema: dict, request: dict) -> dict:
    return j2.fable_body(system, transport_schema(schema), request)


class Judge(j2.Judge):
    def __init__(self, model, *args, **kwargs):
        super().__init__(model, *args, **kwargs)
        if model == j2.FABLE:
            self.body = fable_body

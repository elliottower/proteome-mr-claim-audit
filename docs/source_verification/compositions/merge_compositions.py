# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""One-off merge of compositions/*.json into the dataset dictionary and components table.

Record of the merge run on 2026-09-30. The two tables were edited after it (RELEASES.md), so it is
kept as provenance and is not to be rerun: it rewrites both tables.

Harmonization applied to every component list (old rows included):
  RENAME     synonymous IDs produced by different readers -> one ID
  EPIC       any EPIC_<centre or sub-study> also carries EPIC (one participant source)
  FINNGEN    any list containing FINNGEN also carries the FinnGen legacy cohorts of Kurki 2023
             Supplementary Table 2 (R5), so FINRISK, Health 2000 etc. overlap FinnGen
Flags: a row's includes_ukb / includes_iceland come from the reader's JSON; a flag of `no` on an
incomplete row is written as `unknown` (the guide's rule), except where the JSON says yes.
"""

import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
VERIF = HERE.parent
EXP = VERIF.parents[1] / "experiments" / "02_claims_meta"
DICT = EXP / "dataset_dictionary.csv"
COMP = EXP / "verification" / "dataset_components.csv"
GROUPS = ["cad_hf_af", "stroke_bp_lipid_kidney", "neuro", "psych", "metabolic",
          "immune_resp_biobank", "cancer_covid_other"]
FINNGEN_OBJECT = "FinnGen (all releases): participant sources"
FINNGEN_LEGACY = ["BOTNIA", "COROGENE", "FINRISK", "GENERISK", "HEALTH2000",
                  "HELSINKI_HEART_STUDY", "FINNISH_MIGRAINE", "FINHEALTH2017", "SUPER_FINLAND",
                  "THL_DIABETES", "FINNISH_TWIN_COHORT", "FINNISH_IPF", "FINNAKI"]
RENAME = {"FINNTWIN": "FINNISH_TWIN_COHORT", "CROATIA_KORCULA": "KORCULA",
          "CROATIA_SPLIT": "SPLIT", "HEALTH2000_GENMETS": "HEALTH2000",
          "FINRISK_DILGOM": "FINRISK", "LIFELINES_DEEP": "LIFELINES", "MPP_RES": "MPP",
          "ROTTERDAM": "RS"}
EPIC_PARTS = {"EPIC_CVD", "EPIC_INTERACT", "EPIC_NORFOLK", "EPIC_OBESITY", "EPIC_POTSDAM"}
PQTL_FLAGS = ["INTERVAL", "FENLAND", "ARIC", "AGES", "KORA", "FHS", "IMPROVE", "DECODE"]


def harmonize(ids: set[str]) -> set[str]:
    ids = {RENAME.get(i, i) for i in ids}
    if ids & EPIC_PARTS:
        ids.add("EPIC")
    if "FINNGEN" in ids:
        ids |= set(FINNGEN_LEGACY)
    return ids


def main() -> None:
    dict_rows = list(csv.DictReader(DICT.open()))
    dict_fields = list(dict_rows[0])
    comp_rows = {r["name"]: r for r in csv.DictReader(COMP.open())}
    by_name = {r["name"]: r for r in dict_rows}
    log = []
    for g in GROUPS:
        for o in json.load((HERE / f"{g}.json").open()):
            name = o["row_name"]
            if name == FINNGEN_OBJECT:
                continue
            ids = {c["id"] for c in o["components"]}
            if "STANLEY" in ids and name.startswith("SCALLOP multi-cohort"):
                ids.add("SWEBIC")  # reader mapped SWEBIC rows to STANLEY; keep both IDs
            complete = o["components_complete"]
            ukb, ice = o["includes_ukb"], o["includes_iceland"]
            if complete != "yes":
                ukb = "unknown" if ukb == "no" else ukb
                ice = "unknown" if ice == "no" else ice
            flags = o.get("pqtl_cohort_flags", {})
            present = [k for k in PQTL_FLAGS if k in ids or flags.get(k) == "yes"]
            summary = (f"{len(ids)} participant sources, listed in "
                       f"verification/dataset_components.csv"
                       + (f"; pQTL cohorts among them: {', '.join(present)}" if present else ""))
            claims = ";".join(o.get("claims_files", []))
            notes = " ".join(x for x in (o.get("complete_reason", ""), o.get("notes", "")) if x)
            if o.get("new_row"):
                if name in by_name:
                    raise ValueError(f"new row {name!r} already in the dictionary")
                base = {k: "" for k in dict_fields}
                base.update(side=o.get("side", "outcome"), name=name,
                            aliases=o.get("aliases_proposed", ""), release=o.get("release", ""),
                            source_citation=o.get("source_citation", ""),
                            source_identifier=o.get("source_identifier", ""))
                dict_rows.append(base)
                by_name[name] = base
                log.append(f"added {name}")
            elif name not in by_name:
                raise ValueError(f"row {name!r} not in the dictionary and not marked new")
            r = by_name[name]
            r.update(cohort_components=summary, includes_ukb=ukb, includes_iceland=ice,
                     ancestry=o.get("ancestry") or r["ancestry"],
                     sample_size=o.get("sample_size") or r["sample_size"],
                     source_read=o.get("source_read") or r["source_read"], notes=notes)
            comp_rows[name] = {"name": name, "components": "", "components_complete": complete,
                               "composition_claims": claims}
            comp_rows[name]["_ids"] = ids
            log.append(f"{name}: complete={complete} ukb={ukb} iceland={ice}")
    out_comp = []
    for r in dict_rows:
        c = comp_rows[r["name"]]
        ids = c.pop("_ids", None) or set(c["components"].split("|"))
        c["components"] = "|".join(sorted(harmonize(ids)))
        c.setdefault("composition_claims", "")
        out_comp.append(c)
    with DICT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=dict_fields)
        w.writeheader()
        w.writerows(dict_rows)
    with COMP.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "components", "components_complete",
                                          "composition_claims"])
        w.writeheader()
        w.writerows(out_comp)
    (HERE / "merge_log.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()

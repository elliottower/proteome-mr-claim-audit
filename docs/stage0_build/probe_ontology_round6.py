"""Round-6 probe of the pinned MONDO and EFO files for the outcome-alias completion pass.
Resource files only: no claim, pair, registry record or in-window record.

    modal run docs/stage0_build/probe_ontology_round6.py
"""

import collections
import csv
import datetime
import json
import pathlib
import re

import modal

VOLUME = "proteome-mr-claim-audit-inputs"
MOUNT = pathlib.Path("/vol")
REMOTE = MOUNT / "02_claims_meta"
EXP = pathlib.Path("/exp")
HERE = pathlib.Path(__file__).resolve()
LOCAL_EXP = HERE.parents[2] / "experiments" / "02_claims_meta" if modal.is_local() else EXP
OUT = HERE.parent / "probe_ontology_round6.json"
IGNORE = ["__pycache__", "*.pyc", ".pytest_cache"]
SHOW = ["MONDO:0005044", "HP:0000822", "EFO:0000537", "MONDO:0005148", "HP:0001658",
        "MONDO:0005068", "EFO:0004530", "MONDO:0004981"]
NAMES = ["hypertension", "myocardial infarction", "atrial fibrillation", "obesity", "stroke",
         "heart failure", "type 2 diabetes", "asthma", "osteoporosis", "depression",
         "chronic kidney disease", "migraine", "hypercholesterolemia", "gout"]

image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.5.3", "openpyxl==3.1.5", "pydantic==2.13.5", "rapidfuzz==3.14.6")
         .env({"PYTHONPATH": str(EXP / "scripts")})
         .add_local_dir(LOCAL_EXP / "scripts", str(EXP / "scripts"), copy=True, ignore=IGNORE)
         .add_local_dir(LOCAL_EXP / "verification", str(EXP / "verification"), copy=True)
         .add_local_file(LOCAL_EXP / "dataset_dictionary.csv",
                         str(EXP / "dataset_dictionary.csv"), copy=True)
         .add_local_file(LOCAL_EXP / "reference" / "MANIFEST.json",
                         str(EXP / "reference" / "MANIFEST.json"), copy=True)
         .run_commands(f"ln -s {REMOTE / 'inputs'} {EXP / 'inputs'}",
                       f"ln -s {REMOTE / 'derived'} {EXP / 'derived'}"))
vol = modal.Volume.from_name(VOLUME)
app = modal.App("proteome-mr-probe-ontology", image=image)


def stanzas(path: pathlib.Path):
    cur: list[str] | None = None
    with path.open() as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("["):
                if cur:
                    yield cur
                cur = [] if line == "[Term]" else None
            elif cur is not None and line:
                cur.append(line)
    if cur:
        yield cur


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=16384)
def probe() -> dict:
    from canonical_ids import canonical_outcomes, load_collision_table, outcome_candidates
    from verify_claims import build_outcome_index, canonical_id, compact, load_manifest

    manifest = load_manifest()
    files = {k: EXP / manifest[k]["file"] for k in ("mondo", "efo")}
    result: dict = {"written_utc": datetime.datetime.now(datetime.UTC).isoformat(
        timespec="seconds"),
        "ontology_dirs": {k: sorted(p.name for p in v.parent.iterdir())
                          for k, v in files.items()}}
    shown: dict = {}
    xref_sources: dict = {k: collections.Counter() for k in files}
    hp_xrefs: dict[str, set[str]] = collections.defaultdict(set)      # HP id -> MONDO/EFO ids
    icd_xrefs: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    umls: dict[str, dict[str, set[str]]] = {"hp": collections.defaultdict(set),
                                            "mondo": collections.defaultdict(set)}
    obsolete: set[str] = set()
    label: dict[str, str] = {}
    for key, path in files.items():
        for st in stanzas(path):
            tid = next((canonical_id(l[4:].strip()) for l in st if l.startswith("id: ")), None)
            if tid is None:
                continue
            if any(l.startswith("is_obsolete: true") for l in st):
                obsolete.add(tid)
            for l in st:
                if l.startswith("name: "):
                    label.setdefault(tid, l[6:].strip())
            if tid in SHOW:
                shown[f"{key}:{tid}"] = st[:60]
            for l in st:
                if not l.startswith("xref: "):
                    continue
                m = re.match(r"xref: (\S+)(?:\s+\{(.*)\})?", l)
                target, note = m.group(1), m.group(2) or ""
                prefix = target.split(":", 1)[0]
                srcs = re.findall(r'source="([^"]+)"', note)
                tags = [s for s in srcs if s.startswith("MONDO:")] or ["no_mondo_source_tag"]
                for t in tags:
                    xref_sources[key][f"{tid.split(':')[0]} -> {prefix} [{t}]"] += 1
                if tid.startswith(("MONDO:", "EFO:")) and prefix == "HP":
                    hp_xrefs[target].add(f"{tid} [{'|'.join(tags)}]")
                if tid.startswith(("MONDO:", "EFO:")) and prefix in ("ICD10CM", "ICD10",
                                                                     "ICD10WHO"):
                    icd_xrefs[target.split(":", 1)[1]].add((tid, f"{prefix}|{'|'.join(tags)}"))
                if prefix == "UMLS":
                    if tid.startswith("HP:"):
                        umls["hp"][target].add(tid)
                    elif tid.startswith("MONDO:") and "MONDO:equivalentTo" in tags:
                        umls["mondo"][target].add(tid)
    result["shown"] = shown
    result["xref_sources_top"] = {k: dict(v.most_common(60)) for k, v in xref_sources.items()}

    tiers, names = build_outcome_index(manifest)
    exact, related = tiers[1], tiers[2]
    collision = load_collision_table(EXP / "verification" / "mondo_efo_collision_table.csv")
    other_only = {}
    for name in sorted(exact):
        ids = sorted(exact[name])
        final = canonical_outcomes(ids, collision)
        if final and not any(f.startswith(("MONDO:", "EFO:")) for f in final):
            other_only[name] = final
    by_prefix = collections.Counter("+".join(sorted({f.split(":")[0] for f in v}))
                                    for v in other_only.values())
    hp_shared_umls = {}
    for hp_cui, hp_ids in umls["hp"].items():
        for h in hp_ids:
            hp_shared_umls.setdefault(h, set()).update(umls["mondo"].get(hp_cui, set()))
    counts = collections.Counter()
    examples: dict[str, list] = collections.defaultdict(list)
    for name, final in other_only.items():
        hp = [f for f in final if f.startswith("HP:")]
        if not hp:
            counts["no_hp_identifier"] += 1
            continue
        direct = set().union(*(hp_xrefs.get(h, set()) for h in hp))
        shared = set().union(*(hp_shared_umls.get(h, set()) for h in hp)) - obsolete
        rel = {r for r in related.get(name, set()) if r.startswith(("MONDO:", "EFO:"))}
        key = (f"direct_xref={min(len(direct), 2)},shared_umls={min(len(shared), 2)},"
               f"related_synonym={min(len(rel), 2)}")
        counts[key] += 1
        if len(examples[key]) < 12:
            examples[key].append({"name": name, "hp": hp, "direct": sorted(direct)[:3],
                                  "shared_umls": sorted(f"{s} {label.get(s, '')}"
                                                        for s in shared)[:3],
                                  "related": sorted(f"{r} {label.get(r, '')}" for r in rel)[:3]})
    result["names_with_only_hp_oba_orphanet"] = {
        "names": len(other_only), "by_prefixes": dict(by_prefix),
        "hp_names_by_available_equivalence": dict(sorted(counts.items())),
        "examples": dict(examples)}
    probe_names = {}
    for n in NAMES:
        k = compact(n)
        ids = sorted(exact.get(k, set()))
        hp = [i for i in ids if i.startswith("HP:")]
        probe_names[n] = {
            "exact_ids": ids, "candidates": outcome_candidates(ids, collision),
            "final": canonical_outcomes(ids, collision),
            "related_ids": sorted(related.get(k, set())),
            "hp_direct_xref": sorted(set().union(*(hp_xrefs.get(h, set()) for h in hp))) if hp
            else [],
            "hp_shared_umls": sorted(f"{s} {label.get(s, '')}" for s in set().union(
                *(hp_shared_umls.get(h, set()) for h in hp)) - obsolete) if hp else []}
    result["probe_names"] = probe_names

    with (EXP / "verification" / "epigraphdb_trait_mapping.csv").open(newline="") as f:
        traits = list(csv.DictReader(f))
    not_mapped = [t for t in traits if t["state"] != "mapped"]
    trait_out = []
    for t in not_mapped:
        codes = re.findall(r"\b([A-Z]\d{2}(?:\.\d+)?)\b", t["name"])
        hits = {c: sorted(f"{tid} {label.get(tid, '')} [{how}]"
                          for tid, how in icd_xrefs.get(c, set()) if tid not in obsolete)[:6]
                for c in codes}
        trait_out.append({"name": t["name"], "state": t["state"],
                          "canonical_ids": t["canonical_ids"], "icd_codes": codes,
                          "icd_xref_terms": hits})
    result["epigraphdb_traits_not_mapped"] = trait_out
    result["epigraphdb_traits_by_state_and_rule"] = dict(collections.Counter(
        f"{t['state']}|{t['name_rule']}" for t in traits))
    return result


@app.local_entrypoint()
def main() -> None:
    result = probe.remote()
    target = OUT
    if target.exists():
        target = target.with_name(target.stem + "_" + datetime.datetime.now(
            datetime.UTC).strftime("%Y%m%dT%H%M%SZ") + ".json")
    target.write_text(json.dumps(result, indent=1))
    print(target)


WORDS = [["mean", "corpuscular", "volume"], ["platelet", "volume"], ["creatinine", "urin"],
         ["potassium", "urin"], ["serous", "ovar"], ["forearm"], ["pericarditis", "acute"],
         ["cell", "volume"], ["bone", "mineral", "density"], ["happiness"], ["wellbeing"],
         ["well-being"], ["hearing"], ["anxiety"], ["cough"], ["amyloidosis"],
         ["small", "vessel"], ["large", "artery"], ["flutter"], ["hypercholesterol"]]


@app.function(volumes={str(MOUNT): vol}, timeout=3600, cpu=2.0, memory=16384)
def terms() -> dict:
    from verify_claims import canonical_id, load_manifest
    manifest = load_manifest()
    out: dict = {" ".join(w): [] for w in WORDS}
    for key in ("mondo", "efo"):
        for st in stanzas(EXP / manifest[key]["file"]):
            tid = next((canonical_id(l[4:].strip()) for l in st if l.startswith("id: ")), None)
            name = next((l[6:].strip() for l in st if l.startswith("name: ")), "")
            if tid is None or not tid.startswith(("MONDO:", "EFO:", "OBA:", "HP:")):
                continue
            low = name.lower()
            for w in WORDS:
                if all(x in low for x in w) and len(out[" ".join(w)]) < 40:
                    obsolete = any(l.startswith("is_obsolete: true") for l in st)
                    repl = [l[13:].strip().rsplit("/", 1)[-1] for l in st
                            if l.startswith("replaced_by: ")]
                    entry = f"{key}|{tid}|{name}|obsolete={obsolete}|replaced_by={repl}"
                    if entry not in out[" ".join(w)]:
                        out[" ".join(w)].append(entry)
    return out


@app.local_entrypoint()
def term_names() -> None:
    target = HERE.parent / "probe_ontology_terms_round6.json"
    target.write_text(json.dumps(terms.remote(), indent=1))
    print(target)

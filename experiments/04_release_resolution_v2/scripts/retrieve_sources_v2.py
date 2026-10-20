# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "openpyxl==3.1.5", "xlrd==2.0.1", "python-docx==1.1.2"]
# ///
"""Retrieval of the records of Paper 1 outside the scope for the second release-resolution
registration (PREREG.md, §Study design, item 1, Retrieval; frozen 19 October 2026). Every rule of
the first registration's retrieval (experiments/03_release_resolution/scripts/retrieve_sources.py,
sealed, imported unchanged) holds, with one change: route R2 (the supplementary files Europe PMC
lists) is not requested. No model is called and no source is read for content.

Per record (`retrieve_record`), as in the first registration:
- Europe PMC metadata of the record (its PMCID, its supplementary-file flag, recorded only, and
  the corrections it lists);
- R1: the Europe PMC full-text XML, rendered as in Paper 1, eligible when it has a body;
- R3: for a record with no Europe PMC full text, the file at the open-access location OpenAlex
  gives, when a plain request returns it;
- a correction or erratum Europe PMC links is fetched by R1 as version `correction`; a journal
  record with no full text by R1 or R3 takes, in turn, the preprint records of its family.
Three tries 60 seconds apart; no e-mail address; no browser imitation.

Records (`outside_scope`): the records of Paper 1's amended primary corpus (claim records of
registry_claims.jsonl, the record id being the claim record id without its last `:` part) that
are not among the 266 of the scope, each with its search record and its family's preprints
(`retrieve_sources.scope`, unchanged).
"""

import time

import retrieve_sources as rs


def retrieve_version(client, rec: dict, version: str, store, sleep) -> tuple[list, list, dict]:
    """The sources of one version of a record by R1 and R3, with failures and metadata."""
    sources, failures = [], []
    meta = rs.epmc_meta(client, rec, sleep)
    pmcid = (meta or {}).get("pmcid") or (rec["record_id"] if rec["record_id"].startswith("PPR")
                                          else None)
    info = {"record_id": rec["record_id"], "version": version, "europe_pmc_record": meta is not None,
            "pmcid": pmcid, "europe_pmc_has_supplements": (meta or {}).get("hasSuppl"),
            "corrections": [c for c in ((meta or {}).get("commentCorrectionList") or {})
                            .get("commentCorrection", []) if c.get("type") in rs.CORRECTION_TYPES]}
    full_text = False
    if pmcid:
        url = f"{rs.EPMC}/{pmcid}/fullTextXML"
        r = rs.get(client, url, sleep=sleep)
        text = rs.render_xml(r.content) if r is not None else None
        if text:
            key = store(r.content)
            sources.append({"route": "R1", "version": version, "record_id": rec["record_id"],
                            "url": url, "retrieved_utc": rs.now(), "type": "JATS XML",
                            "stored": key, "sha256": rs.sha256(r.content), "text": text})
            full_text = True
        else:
            failures.append({"route": "R1", "version": version, "url": url,
                             "reason": "no_file" if r is None else "xml_without_body"})
    if not full_text:
        work = rs.openalex_id(rec)
        r = rs.get(client, rs.OPENALEX + work, sleep=sleep) if work else None
        loc = (r.json().get("best_oa_location") or {}) if r is not None else {}
        url = loc.get("pdf_url") or loc.get("landing_page_url")
        f = rs.get(client, url, sleep=sleep) if url else None
        if f is not None:
            key = store(f.content)
            name = "oa.pdf" if f.content[:4] == b"%PDF" else (
                "oa.html" if b"<html" in f.content[:2000].lower() else "oa.bin")
            for part in rs.convert(name, f.content):
                sources.append({"route": "R3", "version": version, "record_id": rec["record_id"],
                                "url": url, "retrieved_utc": rs.now(), "stored": key, **part})
            full_text = any(s["route"] == "R3" and s.get("text") for s in sources)
        else:
            failures.append({"route": "R3", "version": version, "url": url,
                             "reason": "no_open_access_location" if not url else "no_file"})
    info["full_text"] = full_text
    return sources, failures, info


def retrieve_record(client, rec: dict, family_preprints: list[dict], store,
                    sleep=time.sleep) -> dict:
    """Every source of one record by R1 and R3, with failures, under the first registration's
    version rules."""
    versions, sources, failures = [], [], []
    s, f, info = retrieve_version(client, rec, "journal" if rec["kind"] == "journal"
                                  else rec["kind"], store, sleep)
    sources += s
    failures += f
    versions.append(info)
    for c in info["corrections"]:
        if c.get("source") == "MED" and c.get("id"):
            cs, cf, cinfo = retrieve_version(client, {"record_id": c["id"], "pmid": c["id"],
                                                      "kind": "correction"}, "correction",
                                             store, sleep)
            sources += [x for x in cs if x["route"] == "R1"]
            failures += [x for x in cf if x["route"] == "R1"]
            versions.append(cinfo)
    if rec["kind"] == "journal" and not info["full_text"]:
        for pre in family_preprints:
            ps, pf, pinfo = retrieve_version(client, pre, "preprint", store, sleep)
            sources += ps
            failures += pf
            versions.append(pinfo)
            if pinfo["full_text"]:
                break
    readable = [x for x in sources if x.get("text")]
    for x in sources:
        if x.get("text") is not None:
            x["text_sha256"] = rs.sha256(x["text"].encode())
            x["characters"] = len(x["text"])
    return {"record_id": rec["record_id"], "kind": rec["kind"], "finished_utc": rs.now(),
            "versions": versions, "sources": sources, "failures": failures,
            "status": "retrieved" if readable else (
                "source_unreadable" if sources else "no_source")}


def corpus_records(claim_record_ids: list[str]) -> set[str]:
    return {c.rsplit(":", 1)[0] for c in claim_record_ids}


def outside_scope(claim_record_ids: list[str], scope_records: list[str],
                  search_records: dict[str, dict], families: dict) -> list[dict]:
    """The records of the corpus outside the scope, each with its search record and its family's
    preprints, in sorted order of record id."""
    records = sorted(corpus_records(claim_record_ids) - set(scope_records))
    return rs.scope({"records": records}, search_records, families)


def listing(result: dict) -> dict:
    """What of a record's result is committed: ids, routes, versions, statuses, types, counts and
    sha256; no text and no URL."""
    return {"record_id": result["record_id"], "kind": result["kind"], "status": result["status"],
            "versions": [{k: v[k] for k in ("record_id", "version", "europe_pmc_record",
                                            "pmcid", "full_text")} for v in result["versions"]],
            "sources": [{"route": s["route"], "version": s["version"],
                         "record_id": s["record_id"], "type": s.get("type"),
                         "readable": bool(s.get("text")), "reason": s.get("reason"),
                         "sha256": s.get("sha256"), "text_sha256": s.get("text_sha256"),
                         "characters": s.get("characters")} for s in result["sources"]],
            "failures": [{k: f[k] for k in ("route", "version", "reason")}
                         for f in result["failures"]]}

import pathlib, subprocess, shutil
ROOT = pathlib.Path(__file__).parent
ORIG = pathlib.Path.home() / "Documents/GitHub/proteome-mr-claim-audit/experiments/02_claims_meta/scripts"
MUTATIONS = [
 ("funnel.py", "if not (run.gated and i in set(marked))", "if not (i in set(marked))", "test_stage_reports.py"),
 ("funnel.py", 'd["decision"] in ELIGIBLE]\n    same_ids("extraction rows"', 'd["decision"] == "eligible"]\n    same_ids("extraction rows"', "test_stage_reports.py"),
 ("repeat_run_agreement.py", "for number, key in ((1, full_key), (2, pair_key)):", "for number, key in ((1, full_key),):", "test_stage_reports.py"),
 ("repeat_run_agreement.py", "pairs.append((i, partners.pop(0), number))", "pairs.append((i, partners[0], number))", "test_stage_reports.py"),
 ("repeat_run_agreement.py", "return set(a[field]) == set(b[field])", "return a[field] == b[field]", "test_stage_reports.py"),
 ("negative_control_specificity.py", "judged = len(ids) - by[FAILED]", "judged = len(ids)", "test_stage_reports.py"),
 ("negative_control_specificity.py", 'by[NOT_ELIGIBLE] / judged if judged else None', '(judged - by[NOT_ELIGIBLE]) / judged if judged else None', "test_stage_reports.py"),
 ("keyword_prefilter.py", "min(sample_size, len(out))", "len(out)", "test_stage_reports.py"),
 ("select_eligible.py", 'ELIGIBLE = ("eligible", "eligible_count_not_stated", "uncertain")', 'ELIGIBLE = ("eligible", "eligible_count_not_stated")', "test_stage_reports.py"),
 ("canonical_ids.py", "return preferred\n", "return candidates\n", "test_canonical_ids.py"),
 ("canonical_ids.py", "if mondo_first and len(preferred) > 1 and len(mondo) == 1:", "if mondo_first and len(preferred) > 1 and mondo:", "test_canonical_ids.py"),
 ("reference_screen.py", "if not ids and tail:", "if tail:", "test_reference_screen.py"),
 ("reference_screen.py", 'return ICD10_CODE.sub("", name.rsplit(": ", 1)[1].strip()).strip() or None', 'return name.rsplit(": ", 1)[1].strip() or None', "test_reference_screen.py"),
 ("drug_joins.py", "if rule.clinical_trials_only and t.status is None:", "if rule.clinical_trials_only and t.status is not None:", "test_drug_joins.py"),
 ("drug_joins.py", "if rule.unflagged_only and t.quality_controls:", "if rule.unflagged_only and not t.quality_controls:", "test_drug_joins.py"),
 ("drug_joins.py", "(t.n_drugs != 1 or len(t.disease_ids) != 1)", "(t.n_drugs != 1)", "test_drug_joins.py"),
 ("drug_joins.py", "t.status == COMPLETED for t in trials", "t.status is not None for t in trials", "test_drug_joins.py"),
 ("drug_joins.py", "RULES[pair.level].null_result_claims_count or c.direction != NONSIG)", "True)", "test_drug_joins.py"),
 ("hub_proteins.py", "and (count_null or c.direction != NONSIG)]", "]", "test_hub_proteins.py"),
 ("pathway_enrichment.py", "if c.direction == NONSIG and not count_null:", "if False:", "test_pathway_enrichment.py"),
 ("pathway_enrichment.py", "out |= attached - {None}", "out |= set()", "test_pathway_enrichment.py"),
 ("link_families.py", "if len({find(a.record_id) for a in matches}) == 1:", "if matches:", "test_assemble_and_sensitivity.py"),
 ("assemble_registry.py", 'records = [r for r in records if r.kind != "other"]', "pass", "test_assemble_and_sensitivity.py"),
 ("assemble_registry.py", "{rid: d for rid, d in decision.items() if rid not in copies})", "decision)", "test_assemble_and_sensitivity.py"),
 ("assemble_screening_set.py", 'if w.get("type") in OPENALEX_JOURNAL_TYPES else "other"', 'if True else "other"', "test_screening_set.py"),
 ("assemble_screening_set.py", 'if r["source"] in EPMC_JOURNAL_SOURCES else "other"', 'if True else "other"', "test_screening_set.py"),
 ("citation_chase.py", 'f"openalex:{\'|\'.join(batch)}{floor}"', 'f"openalex:{\'|\'.join(batch)}"', "test_citation_chase.py"),
 ("fetch_fulltext.py", 'if record.get("abstract_source") != "pubmed":', 'if False:', "test_fetch_fulltext.py"),
 ("fetch_fulltext.py", "if not target.exists():", "if True:", "test_fetch_fulltext.py"),
 ("fulltext_concordance.py", 'out[fam] = ("extracted" if extraction_status.get(f["full_text_record"]) == "ok"', 'out[fam] = ("extracted" if True', "test_fulltext_concordance.py"),
 ("therapeutic_areas.py", "if all(s & picked for s in sets):", "if any(s & picked for s in sets):", "test_therapeutic_areas.py"),
 ("therapeutic_areas.py", "return frozenset(by_distance[min(by_distance)]), \"nearest_ancestor\"", "return frozenset(by_distance[max(by_distance)]), \"nearest_ancestor\"", "test_therapeutic_areas.py"),
 ("therapeutic_areas.py", "return found - NOT_DISEASE_AREAS, rule", "return found, rule", "test_therapeutic_areas.py"),
 ("hub_proteins.py", "size = len(distinct) if distinct_areas else cover", "size = len(distinct)", "test_hub_proteins.py"),
 ("manual_dataset_coding.py", "if first and first == second:", "if first:", "test_manual_dataset_coding.py"),
 ("manual_dataset_coding.py", 'if row["author_confirms"] != "yes":', "if False:", "test_manual_dataset_coding.py"),
 ("manual_dataset_coding.py", 'if r["status"] != status:', "if False:", "test_manual_dataset_coding.py"),
 ("build_registry.py", 'row = manual.get((c["pmid"], side, name))', 'row = manual.get((c["pmid"], "pqtl", name))', "test_manual_dataset_coding.py"),
 ("build_registry.py", "manually_coded=any(c.manual_dataset_codes for c in allrecs))", "manually_coded=False)", "test_manual_dataset_coding.py"),
 ("platform_list_sources.py", "if found != source.sha256:", "if False:", "test_platform_lists.py"),
 ("platform_list_sources.py", "if not source.filter_column or r[source.filter_column] == source.filter_value]", "]", "test_platform_lists.py"),
 ("pathway_enrichment.py", "lists[cell] = frozenset().union(*(lists[p] for p in parts))", "lists[cell] = lists[parts[0]]", "test_platform_lists.py"),
 ("pathway_enrichment.py", 'cell = (r.get("alternative_assay_list") if alternative else "") or r["assay_list"]', 'cell = r["assay_list"]', "test_platform_lists.py"),
 ("reference_screen.py", "if aliases and name in aliases:", "if False:", "test_reference_screen.py"),
 ("reference_screen.py", 'as_written_only and r.get("name_rule") != "as_written") else None', 'as_written_only and r.get("name_rule") == "after_last_colon") else None', "test_reference_screen.py"),
 ("assay_backgrounds.py", "kept = frozenset(printed & reviewed)", "kept = frozenset(printed)", "test_platform_lists.py"),
 ("registry_indices.py", "return sorted(areas_of_outcome(outcome)[0]) or [NO_AREA]", "return sorted(areas_of_outcome(outcome)[0])[:1] or [NO_AREA]", "test_registry_indices.py"),
 ("build_outcome_aliases.py", "if len(set(live)) != 1:", "if not live:", "test_outcome_aliases.py"),

]
survived = []
for name, old, new, test in MUTATIONS:
    target = ROOT / "scripts" / name
    text = (ORIG / name).read_text()
    assert old in text, (name, old)
    target.write_text(text.replace(old, new, 1))
    r = subprocess.run(["python", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", test], cwd=ROOT / "tests", capture_output=True, text=True)
    if r.returncode == 0:
        survived.append((name, old))
    target.write_text(text)
print(len(MUTATIONS), "mutations;", len(MUTATIONS) - len(survived), "killed")
for s in survived: print("SURVIVED:", s)

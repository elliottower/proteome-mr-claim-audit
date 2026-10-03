"""Counts only: union sizes with and without Q3, and Q3 restricted to MR/genetic terms."""
import json
from count_queries import Q, MR, TARGET, PQTLB, DATE, pubmed_ids

GEN = '(' + MR[1:-1] + ' OR pQTL[tiab] OR pQTLs[tiab] OR "protein quantitative trait*"[tiab] OR "genetically predicted"[tiab] OR "genetically proxied"[tiab] OR "cis-MR"[tiab])'
ids = {k: set(pubmed_ids(q)) for k, q in Q.items()}
q3g = set(pubmed_ids(f"{TARGET} AND {PQTLB} AND {GEN} AND {DATE}"))
res = {
    "union_all_four": len(ids["Q1"] | ids["Q2"] | ids["Q3"] | ids["Q4"]),
    "union_Q1_Q2_Q4": len(ids["Q1"] | ids["Q2"] | ids["Q4"]),
    "Q3_restricted_to_genetic_terms": len(q3g),
    "union_Q1_Q2_Q4_plus_Q3_genetic": len(ids["Q1"] | ids["Q2"] | ids["Q4"] | q3g),
    "Q3_only_records_not_in_other_queries": len(ids["Q3"] - (ids["Q1"] | ids["Q2"] | ids["Q4"])),
}
json.dump(res, open("query_union_counts_2026-09-30.json", "w"), indent=2)
print(res)

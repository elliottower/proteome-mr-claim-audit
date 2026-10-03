"""Canonical pair identifiers for the registry: UniProt accession × canonical outcome identifier.

Protein. The verifier maps a protein name to HGNC entries. Each HGNC entry's accessions are the
`uniprot_ids` of the pinned HGNC complete set, kept only when the accession is an entry of the
pinned UniProtKB human reviewed file. A record's protein identifier is the union of the
accessions of all its HGNC entries:

    mapped               exactly one accession (also when several HGNC entries, such as a gene
                         and its readthrough, share one accession)
    multiple_uniprot     more than one accession: a protein complex or heteromer named as one
                         analyte (several HGNC entries), or one gene with several reviewed
                         entries (for example GNAS); no pair, counted `pair_ambiguous`
    no_uniprot           no reviewed accession; counted as unmapped
    no_hgnc              the verifier returned no HGNC entry

Outcome. Each Mondo/EFO identifier the verifier returned is replaced by its canonical
identifier from `verification/mondo_efo_collision_table.csv` (identifiers not in the table are
their own canonical identifier); the record's outcome is the set of canonical identifiers.
A row flagged `branch_disagreement` (MONDO and EFO place the concept on opposite sides of the
disease/trait line; six rows in the pinned table) is not merged: both of its identifiers stay
their own canonical identifiers, so "multiple sclerosis symptom measurement" (EFO:0803536) and
multiple sclerosis (MONDO:0005301) are separate keys.
The verifier also returns terms that the EFO file imports from HP, OBA and Orphanet. A canonical
outcome is a Mondo term for a disease and an EFO term for a trait, so when a name gives at least
one MONDO or EFO identifier, its identifiers from other ontologies are dropped ("rheumatoid
arthritis" is the label of MONDO:0008383 and of HP:0001370; the outcome is MONDO:0008383). A
name that gives only such identifiers keeps them. Two MONDO or EFO identifiers are never
resolved against each other in the primary analysis; the sensitivity analysis
`shared_names_mondo_first` takes the MONDO identifier of a name that gives exactly one MONDO
identifier beside EFO identifiers.
Exactly one gives a pair; more than one is `pair_ambiguous`. The source identifiers are kept on
the record beside the canonical one.

Phenotype cross-references. A name that gives no MONDO or EFO identifier can still name a
disease: "hypertension" is the label of HP:0000822 only, and the disease term is MONDO:0005044.
When every identifier of such a name is a phenotype term listed in the committed table
`verification/phenotype_cross_references.csv` (the HP terms that exactly one canonical MONDO or
EFO term cross-references in the pinned MONDO file; scripts/outcome_alias_completion.py), and
the table gives them all the same single term, the outcome is that term. Otherwise the name
keeps its identifiers. The table is read with the collision table, from the same folder, and
held in the same mapping under keys that begin `phenotype_xref:`. The sensitivity analysis
`without_phenotype_cross_references` leaves it out (`without_phenotype_xrefs`).
"""

import collections
import csv
import pathlib
from typing import Literal

ProteinState = Literal["mapped", "multiple_uniprot", "no_uniprot", "no_hgnc"]
CANONICAL_ONTOLOGIES = ("MONDO:", "EFO:")
PHENOTYPE_XREFS = "phenotype_cross_references.csv"
PHENOTYPE_XREF_KEY = "phenotype_xref:"


def load_hgnc_uniprot(hgnc_tsv: pathlib.Path, uniprot_tsv: pathlib.Path
                      ) -> dict[str, frozenset[str]]:
    """Approved HGNC ID -> reviewed UniProt accessions in the pinned files."""
    with uniprot_tsv.open() as f:
        reviewed = {r["Entry"] for r in csv.DictReader(f, delimiter="\t")}
    out: dict[str, frozenset[str]] = {}
    with hgnc_tsv.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["status"] != "Approved":
                continue
            accs = {a.strip() for a in r["uniprot_ids"].strip('"').split("|") if a.strip()}
            out[r["hgnc_id"]] = frozenset(accs & reviewed)
    return out


def protein_accession(hgnc_ids: list[str], hgnc_uniprot: dict[str, frozenset[str]]
                      ) -> tuple[str | None, ProteinState, list[str]]:
    """(accession or None, state, every candidate accession)."""
    if not hgnc_ids:
        return None, "no_hgnc", []
    accs = sorted(frozenset().union(*(hgnc_uniprot.get(h, frozenset()) for h in hgnc_ids)))
    if not accs:
        return None, "no_uniprot", []
    if len(accs) > 1:
        return None, "multiple_uniprot", accs
    return accs[0], "mapped", accs


def load_collision_table(path: pathlib.Path, phenotype_xrefs: pathlib.Path | None = None
                         ) -> dict[str, frozenset[str]]:
    """Source identifier (Mondo or EFO-file term) -> its canonical identifiers over all rows,
    and, under keys `phenotype_xref:<HP term>`, the phenotype cross-references: the table
    `phenotype_xrefs`, by default the file `phenotype_cross_references.csv` beside the collision
    table when there is one."""
    canon: dict[str, set[str]] = collections.defaultdict(set)
    with path.open() as f:
        for r in csv.DictReader(f):
            if "branch_disagreement" in r["conflicts"].split("|"):
                canon[r["mondo_id"]].add(r["mondo_id"])
                canon[r["efo_id"]].add(r["efo_id"])
                continue
            canon[r["mondo_id"]].add(r["canonical_id"])
            canon[r["efo_id"]].add(r["canonical_id"])
    xrefs = phenotype_xrefs or path.with_name(PHENOTYPE_XREFS)
    if xrefs.exists():
        with xrefs.open() as f:
            for r in csv.DictReader(f):
                canon[PHENOTYPE_XREF_KEY + r["phenotype_id"]].add(r["canonical_id"])
    return {k: frozenset(v) for k, v in canon.items()}


def without_phenotype_xrefs(table: dict[str, frozenset[str]]) -> dict[str, frozenset[str]]:
    """The collision table without the phenotype cross-references."""
    return {k: v for k, v in table.items() if not k.startswith(PHENOTYPE_XREF_KEY)}


def phenotype_term(candidates: list[str], table: dict[str, frozenset[str]]) -> str | None:
    """The single MONDO or EFO term that the pinned MONDO file cross-references to every
    identifier of a name, or None. Only phenotype terms are in the table, so a name with a
    MONDO or EFO identifier gives None."""
    crossed = [table.get(PHENOTYPE_XREF_KEY + c) for c in candidates]
    if not candidates or not all(crossed):
        return None
    terms = frozenset().union(*crossed)
    return next(iter(terms)) if len(terms) == 1 else None


def outcome_candidates(ids: list[str], table: dict[str, frozenset[str]]) -> list[str]:
    """Every canonical identifier of the verifier's identifiers, whatever its ontology."""
    return sorted(frozenset().union(*(table.get(i, frozenset({i})) for i in ids))) if ids \
        else []


def canonical_outcomes(ids: list[str], table: dict[str, frozenset[str]],
                       mondo_first: bool = False) -> list[str]:
    """The canonical identifiers of a record's outcome: its MONDO and EFO candidates when it
    has any; otherwise the single term the phenotype cross-references give its candidates, when
    they give one; otherwise all its candidates. `mondo_first` is the sensitivity reading
    `shared_names_mondo_first`: when a name gives exactly one MONDO identifier beside EFO
    identifiers (one label carried by a MONDO term and an EFO-file term that the pinned files
    do not assert to be one concept), the MONDO identifier is taken."""
    candidates = outcome_candidates(ids, table)
    crossed = phenotype_term(candidates, table)
    if crossed is not None:
        return [crossed]
    preferred = [c for c in candidates if c.startswith(CANONICAL_ONTOLOGIES)] or candidates
    mondo = [c for c in preferred if c.startswith("MONDO:")]
    if mondo_first and len(preferred) > 1 and len(mondo) == 1:
        return mondo
    return preferred


def canonical_pair(protein_ids: list[str], outcome_ids: list[str],
                   hgnc_uniprot: dict[str, frozenset[str]],
                   collision: dict[str, frozenset[str]]) -> tuple[str, str] | None:
    """(UniProt accession, canonical outcome identifier), or None when either is not single."""
    acc, state, _ = protein_accession(protein_ids, hgnc_uniprot)
    outcomes = canonical_outcomes(outcome_ids, collision)
    return (acc, outcomes[0]) if state == "mapped" and len(outcomes) == 1 else None

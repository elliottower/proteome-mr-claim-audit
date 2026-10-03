"""Build the bibliography of the works this registration relies on, and map each claims file to it.

Every DOI a claims file under `claims/` names, plus the DOIs of works the preregistration cites
that have no claims file, is added to `experiments/02_claims_meta/references.bib` with
`citations add --doi`, which fetches the registry record and writes every listed author. A DOI
already in the file is skipped, so a stopped run is resumed by running it again.

The claims files name their source by a per-file key (`aragam2022cad_supp_table1`), and several
files can belong to one work. `docs/source_verification/claims_to_bibkey.csv` maps each claims
file to the bibliography key of the work its DOI names.

Run from the repository root with the `citations` build of reproducible-science main:

    uv run --project ~/Documents/GitHub/reproducible-science-main \
        python docs/source_verification/build_references_bib.py
"""

import contextlib
import csv
import io
import pathlib
import re

import yaml
from citations import add as citations_add
from citations.exceptions import BibFileError

BIB = pathlib.Path("experiments/02_claims_meta/references.bib")
MAP = pathlib.Path("docs/source_verification/claims_to_bibkey.csv")
CLAIMS = pathlib.Path("claims")

# Works the preregistration cites by name that no claims file pins. Each DOI was read off the
# Europe PMC or OpenAlex record whose first author and year match the citation.
CITED_WITHOUT_CLAIMS = {
    "10.1093/brain/awad070": "Lin, Zhou and Xu 2023, Brain (PMID 36864689)",
    "10.1038/s41588-024-01854-z": "Razuvayevskaya et al. 2024, Nat Genet",
    "10.1093/eurheartj/ehaf186": "Chen, Zhao and Fu 2025, Eur Heart J",
    "10.1093/bioinformatics/btae519": "Liu and Gaunt 2024, Bioinformatics",
    "10.1038/s41598-026-41818-3": "Sobczyk and Gaunt 2026, Sci Rep",
    "10.64898/2026.02.23.26346731": "Karim et al. 2026, medRxiv",
}

DOI_FIELD = re.compile(r"^\s*doi\s*=\s*\{([^}]*)\}", re.IGNORECASE | re.MULTILINE)
ENTRY = re.compile(r"^@\w+\{([^,]+),", re.MULTILINE)
SPACED_KEY = re.compile(r"plus (.+?), and was restored")


def keys_by_doi(text: str) -> dict[str, str]:
    """The key of each entry in a .bib, by its lower-cased DOI."""
    found: dict[str, str] = {}
    starts = [(m.start(), m.group(1)) for m in ENTRY.finditer(text)]
    for i, (start, key) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        doi = DOI_FIELD.search(text[start:end])
        if doi:
            found[doi.group(1).strip().lower()] = key
    return found


def claims_dois() -> dict[str, list[str]]:
    """Each DOI a claims file names, with the claims files naming it."""
    by_doi: dict[str, list[str]] = {}
    for path in sorted(CLAIMS.glob("*.yaml")):
        doi = (yaml.safe_load(path.read_text())["source"].get("doi") or "").strip().lower()
        if doi:
            by_doi.setdefault(doi, []).append(path.name)
    return by_doi


def main() -> None:
    BIB.touch()
    by_doi = claims_dois()
    wanted = sorted(set(by_doi) | set(CITED_WITHOUT_CLAIMS))
    failed: list[str] = []
    for doi in wanted:
        if doi in keys_by_doi(BIB.read_text()):
            continue
        said = io.StringIO()
        try:
            with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
                code = citations_add.main([str(BIB), "--doi", doi])
        except BibFileError as error:
            # `citations add` derives a key from a family name with a space in it ("Lango Allen")
            # and then cannot read that key back; the file is restored. Add it again with the
            # space removed (reported to the tools session).
            derived = SPACED_KEY.search(str(error))
            if derived is None:
                raise
            with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
                code = citations_add.main(
                    [str(BIB), "--doi", doi, "--key", re.sub(r"[^0-9A-Za-z]", "", derived.group(1))]
                )
        if code != 0:
            failed.append(doi)
            print(f"not added  {doi}: {said.getvalue().strip().splitlines()[-1:] or ['']}")

    keys = keys_by_doi(BIB.read_text())
    with MAP.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["claims_file", "doi", "bibkey"])
        for doi, files in sorted(by_doi.items()):
            for name in files:
                writer.writerow([name, doi, keys.get(doi, "")])
    print(f"{len(keys)} entries in {BIB}; {len(failed)} DOIs not added")


if __name__ == "__main__":
    main()

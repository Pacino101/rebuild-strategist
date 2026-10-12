# Anonymisation statement

This directory is an anonymised version of a real commercial project. This document explains **what was anonymised, how it was done, and the residual risk**.

> ⚠️ **This document deliberately does not include the original names or a substitution mapping table.**
> A table that spells out "XX Company → Owner A" amounts to reversing the anonymisation again.
> If you need to verify whether the anonymisation is thorough, use the "How to self-check" section below.

---

## 1. Which categories were anonymised

| Category | Treatment | Illustrative example (**example, not the original text**) |
|---|---|---|
| **The owner (commissioning party)** | All replaced with role codes | Group name, shareholder names, subsidiary names, description of ownership type → "Owner A (municipally-owned state enterprise)" |
| **Site information** | All replaced with pseudo place names | City, administrative district, subdistrict, road, street number, metro station name → "this city", "District L", "Subdistrict J", "Road P", "Station D" |
| **The operator (operating party)** | All replaced with role codes | Company name, product name, team identifier → "the operator" / "REBUILD decision process" |
| **Ownership and title information** | Deleted or replaced | Name of the owning entity, title registration number, property exchange and announcement dates |
| **Competitor entities** | Replaced with codes | Competitor apartment brand names, their title holders, their park names → "competitors K1–K4" |
| **Surrounding institutions** | Replaced with codes | Hospital, park and commercial-district names → "Hospitals A–C", "Parks 1–5" |
| **Research data sources** | Replaced with codes | Research institutions and data service providers → "research institution A/B", "data service provider C" |
| **Policy document numbers** | Generalised | Specific issuing document numbers → "this city's regulatory document on housing rental (year withheld)" |
| **File names** | Neutralised | File names containing place names and project names → `01_合作模式研究报告.txt` |
| **Local paths** | Erased | Absolute paths containing a user name → `<local path withheld>` |
| **Project code** | Replaced | Internal project identifier → `metro-apartment` |

---

## 2. What is deliberately retained

| Retained item | Why it is retained |
|---|---|
| **All amounts, areas, room counts, rents, ratios and periods** | These are "the data used to run the analysis"; without them the analysis cannot be reproduced |
| **All calculation results and model outputs** | This is where the value of the case lies |
| **Age, income and rent-affordability ranges of the customer personas** | Range data cannot be traced to a specific individual |
| **Industry macro data** | Public statistics such as city-level occupancy rates and rents |
| **The substance of the compliance requirements** | The constraint itself is retained (such as "the rent must be lower than the market rent for comparable quality in the same location"); only the locatable document number is removed |
| **Brand and creative expression** | Proposition, slogan, visual motif — generalised along with the place names; what is retained is the creative logic |
| **The plan's own defects and conflicts** | The conflicts recorded in `SKILL_EVALUATION.md` **were not glossed over in any way**; this is part of the case's credibility |

**No named personal information was found** (contacts, persons in charge, case handlers) in the original material;
if anything was missed, please report it in the manner described in the next section.

---

## 3. Method and verification

**Deterministic substitution** was used rather than manual rewriting, to guarantee:

1. **Auditability** — the substitution rules are a one-off script, checkable item by item;
2. **No new content introduced** — numbers or conclusions will not be changed inadvertently in the course of rewriting;
3. **Re-verifiability** — the anonymised text can still be run through the original scripts to produce identical results (see below).

Verification method:

```bash
# 1. All scripts can still reproduce end to end, with figures identical to those before anonymisation
cd rebuild && python3 scripts/run_all.py

# 2. Generic pattern scan: no company suffixes, specific street numbers, metro station names or policy document numbers should appear
grep -rE "[一-龥]{2,12}(有限公司|集团|研究院|事务所)" .
grep -rE "[一-龥]{2,6}(路|街|道)[0-9]+号" .
grep -rE "/Users/" .
```

All three should produce no output.

---

## 4. Residual risk (stated honestly)

**Anonymisation cannot be made zero-risk. The following could still allow the identity to be inferred:**

1. **The data combination may itself be fingerprinting.** The combination of total floor area (retained to two decimal places), room count, capital contribution and
   price tiers may be enough for someone familiar with that district's market to locate the project. **This is the price necessarily paid for retaining the analysis data** —
   change the numbers and the case loses its reproduction value.
2. **The timeline is retained.** The preparation date and the planned opening month were not offset.
3. **The policy environment can be inferred.** The "conversion of non-residential existing housing into subsidised rental housing" channel does not exist in every city;
   retaining that constraint narrows the range of cities.
4. **Competitor characteristics remain.** The codes replaced the names, but structural characteristics such as "government-partnered talent apartments, bachelor's degree threshold, targeted allocation"
   are unchanged.

**Conclusion: this case is suitable for method demonstration and teaching, but not as public material that is completely untraceable.**
If your compliance requirements are stricter, use only `project.json` (purely structured data, containing no narrative material).

---

## 5. What to do if you find something missed

If you find any identifiable information in this directory, please report it privately through the repository's
**Security → Report a vulnerability**, and do not open a public issue.
See [`SECURITY.md`](../../SECURITY.md) in the repository root.

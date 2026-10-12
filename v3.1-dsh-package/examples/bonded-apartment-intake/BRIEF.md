# Decision brief — 75-room bonded apartment conversion

> **This is an illustrative intake brief, not real client data.** It is written to be realistic
> enough to exercise the whole REBUILD loop, and every figure is either given with a stated source
> or explicitly marked as an assumption so the skill has something to grade. Use it as a fixture:
> drop it into a session and ask for a `FULL_STRATEGY` or `GROWTH_DIAGNOSIS` run.

## The request, as the client put it

> "我们有一栋旧物业，想改成长租公寓。合作方出钱装修，我们负责运营。你帮我做一个品牌营销全案，
> 重点是怎么把房子租出去，还有怎么定价。"

The client asked for a **brand marketing plan**. The decision actually in front of them is narrower
and harder: *should the operator sign a bond-backed revenue-share deal at this rent level, and what
would have to be true for it to pay back?*

## 1. Asset

| Item | Value | Source / status |
|---|---|---|
| Location | Subway-adjacent, tier-2 city, inner district | given |
| Walk to metro | ~580 m to a two-line interchange | map lookup, retrieved 2026-09, **UNVERIFIED** |
| Total floor area | 2,751 m² | title registry pre-announcement, **FACT** |
| Certificate use | Industrial / "non-residential" | registry, **FACT** |
| Units planned | 75 | operator plan, **DECISION** |
| Average unit area | 25.7 m² usable / 36.7 m² gross incl. common area | derived, **INTERPRETATION** |

## 2. Deal structure

| Item | Value | Status |
|---|---|---|
| Landlord contribution | 3,000,000 CNY renovation, paid by landlord | given, **FACT** |
| Operator bond | 1,000,000 CNY performance bond, refundable | given, **FACT** |
| Revenue split | landlord takes a monthly share; operator retains the rest | given, **INTERPRETATION** of "按月分红" |
| Term | 8 years minimum if converted under the affordable-rental channel; negotiable to 12 for a state-owned landlord | policy document, **HYPOTHESIS** |

## 3. Rent structure proposed

| Unit size | Monthly rent |
|---|---|
| 18 m² | 1,620 |
| 22 m² | 1,980 |
| 25 m² | 2,250 |
| 29 m² | 2,610 |
| 36 m² | 3,150 |
| **Blended** | **~2,182 / unit** |
| **Per m²** | **89.7 / m²·month** |

Benchmark claimed: the sub-district's official long-stay reference is **90 CNY/m²·month**, and the
plan prices just below it. **Source: secondary, undated, not attached — grade C at best.**

## 4. Targets the plan commits to

| Target | Value | Status |
|---|---|---|
| Occupancy at month 6 | ≥ 88% | plan commitment, **HYPOTHESIS** |
| Occupancy at month 12 | ≥ 93% | stated as "industry steady state", **source not given** |
| Opening marketing budget | 400,000 CNY | plan, **DECISION** |
| CAC | ≤ 4,500 CNY per lease | plan, **HYPOTHESIS** |
| Payback | ≈ 1.9 years | plan, **HYPOTHESIS** — basis not shown |

## 5. What is NOT in the brief

Deliberately absent, because a real brief rarely contains it and the point of the exercise is to see
what the skill does about that:

- no operating cost structure (staffing, utilities, cleaning, maintenance, platform commission, tax)
- no competitor rents or actual occupancy for comparable buildings nearby
- no demand-side evidence of any kind — no enquiries, no waitlist, no tour data
- no lease-up curve, only a month-6 endpoint
- no definition of how the landlord share is computed, or on what base
- no sensitivity analysis
- no statement of who can veto, or what happens if the policy channel closes

## 6. Suggested prompts

```
Load the rebuild-strategist skill. Read examples/bonded-apartment-intake/BRIEF.md.
Run AUDIT mode on the rent and occupancy plan. Show your arithmetic.
```

```
Run GROWTH_DIAGNOSIS on this brief. Build the operating-side unit economics,
then give me the lease-up curve you think the 400k budget can actually buy.
State every assumption you had to add.
```

```
Run RED_TEAM. I am the operator. Find the assumptions that would make me lose
my 1,000,000 bond, and give me kill criteria.
```

## 7. What a good run should produce

Non-negotiables, from the skill's own gates:

- the 1.9-year payback is challenged, because its basis is not shown and no cost structure was given;
- the 88% / 93% occupancy targets are labelled `HYPOTHESIS`, not fact;
- **Gate E does not pass clean** — there is no demand-side evidence, so the run must either
  `PASS_WITH_GAPS` with a named validation plan or return `BLOCKED`;
- the CAC claim is tested against the budget: can 400,000 CNY actually buy 88% of 75 units?
- the operator's downside is quantified — what occupancy destroys the bond;
- the deliverable ends with a decision page and named stop rules, not a brand story.

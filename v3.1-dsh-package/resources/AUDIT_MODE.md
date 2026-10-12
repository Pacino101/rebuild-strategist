# AUDIT mode — specification

Use when the user supplies an existing proposal, deck, plan or report and asks what is wrong with it.
This mode is the highest-value use of the skill, and the one most often done badly.

**The default failure is review resonance.** A reviewer reads the document in the author's order,
agrees with the parts that already have supporting material, and concludes "broadly sound, local
optimisations needed" — which is exactly the conclusion the author designed the document to produce.
Everything below exists to break that.

## Step 0 — establish the baseline before judging anything

Do these first, in order. Skipping them is what produces a pleasant, useless review.

1. **Read every supplied document completely.** Not a sample. Contradictions in this mode are found by
   cross-reading, and they are usually the most valuable finding in the file.
2. **Check for existing state.** If `.rebuild/state.json` exists, load it and resume. If it does not,
   say so plainly and proceed — **do not demand a state file first**.
3. **Recompute every number you can.** See the arithmetic worksheet. A figure you did not recompute is
   a figure you have not audited.
4. **Build the cross-document reconciliation table** whenever more than one document is supplied.
   Most real engagements contain two or three.

## Step 1 — what the author asked, and what is actually being decided

State both, separately:

- **SOURCE says the problem is** … (the request as framed)
- **REBUILD reframes it as** … (the decision actually in front of the reader)

If these are the same, you have probably not reframed. In practice the request is almost always a
*deliverable* ("make me a marketing plan") while the decision is a *commitment* ("should I sign this").

## Step 2 — the seven judgement questions

Answer all seven. Each maps to a verdict tag.

| # | Question | If the answer is bad |
|---|---|---|
| 1 | Which judgements already hold, and on what evidence? | `KEEP` — say so explicitly; uncredited good work gets deleted by the next editor |
| 2 | Which parts are implicit methodology — asserted as a framework but never argued? | `VALIDATE` — name the assumption that carries it |
| 3 | Which claims lack evidence, and how far above their grade are they used? | `VALIDATE` or `DELETE` |
| 4 | Where does the logic break — a conclusion whose middle steps are missing? | `UPGRADE` |
| 5 | Which parts are information piled up rather than analysis? | `DELETE` |
| 6 | Which strategic choices were never actually made — no alternatives, no trade-off? | `UPGRADE` (and the B gate blocks) |
| 7 | What is missing on business, customer, growth or execution? | `UPGRADE` |

### The four verdict tags

| Tag | Means | Granularity |
|---|---|---|
| **KEEP** | Holds as-is. State why, so a later editor does not remove it. | Section or claim |
| **UPGRADE** | The direction is right; the reasoning, evidence or quantification is missing or wrong. Say exactly what to add. | Claim or argument |
| **DELETE** | Should not survive: unsupported, superseded, duplicated, or decoration. Say what replaces it, or say nothing replaces it. | Passage |
| **VALIDATE** | Cannot be judged on the supplied material. Name the cheapest test, its owner and its threshold — **fixed before the test runs**. | Assumption |

Tag at the level of the claim, not the page. A section may contain KEEP, UPGRADE and DELETE items.

## Step 3 — severity of findings

Gate statuses describe the project; findings describe the document. They are separate scales and both
are required.

| Severity | Test | Consequence |
|---|---|---|
| **BLOCKING** | If this is not fixed, the decision cannot responsibly be made | Named as a stop condition; the relevant gate cannot pass |
| **MATERIAL** | Would change the conclusion's direction or magnitude | Must appear in the decision page |
| **MINOR** | Precision, rounding, labelling, wording | List and move on — do not let these dilute the blocking items |

Rank by **whether the decision changes**, never by how wrong the arithmetic looks. A spectacular
arithmetic error in an appendix outranks nothing; a rounding choice that flips a compliance line outranks
almost everything.

**One reported rounding rule:** when a rounding direction favours the conclusion (a bound rounded down
so a threshold appears to hold), report it as a finding. It is not a typo; it is a thumb on the scale.

## Step 4 — output shape

```
1. One-line judgement                     (mandatory — the actual problem)
2. Findings, ordered by severity          BLOCKING → MATERIAL → MINOR, with source locations
3. Arithmetic and reconciliation tables    recomputed values, gaps, and the nature of each gap
4. Gate verdicts                           R / E / B / U / I / D with reasons
5. Red Team                                the angles that matter here, not all nine by rote
6. Keep list                               what must survive
7. Decision page                           decision, recommendation, rejected options,
                                           unit-economics line, what would change the answer,
                                           approvals needed, kill criteria
```

**AUDIT does not require the 15-section FULL_STRATEGY order**, and does not require a 7/30/90-day plan
unless the user asks for one. Substructure follows severity, not the document's chapter order.

**Never rewrite the proposal.** Audit it. Producing a new strategy instead of a verdict is the most
common way this mode fails, and it deprives the user of the judgement they asked for.

### Do not invent the alternatives

If the audited document claims a chosen option but never states the others, **do not manufacture
options on the author's behalf** — you lack their data and it oversteps the mandate. Instead: record
that the comparison is absent, block the B gate, and list the dimensions a real comparison would have
to cover (upside, customer relevance, defensibility, unit economics and cash, capability, time to
evidence, complexity and downside, reversibility). Rebuilding the choice is a different engagement.

## Step 5 — what a passing audit must contain

- every headline number recomputed, or an explicit statement of why it could not be;
- every cross-document conflict reported as a finding, with the magnitude of the gap;
- a Keep list that protects the parts that are right;
- gate verdicts that can block;
- a decision page that names a single next action.

If no number could be recomputed and no conflict was found across multiple documents, say that
plainly — but check first, because it is rare.

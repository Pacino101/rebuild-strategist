# Security and ethics

This skill does work that can cost money, touch customers, and change live systems. That makes a
plain statement of its boundaries part of the product, not boilerplate.

## What this skill will never do on its own

The skill holds these as hard rules, and `tests/SMOKE_TESTS.md` tests two of them (T06, T07):

| Action | Required before it may happen |
|---|---|
| Publish or schedule public content | Explicit approval at the moment of action, plus a connected and verified tool |
| Send messages to customers or leads | Explicit approval, a lawful consent basis, and a verified tool |
| Spend money, or change bids/budgets on a live campaign | Explicit approval, with the cap stated |
| Change or bulk-import CRM records | Explicit approval |
| Export sensitive or personal data | Denied by default |
| Destructive or irreversible operations | Confirmation immediately before execution — not earlier in the conversation |

A draft is always available. The skill's default for anything external is **draft, then stop and ask.**

## The agent cannot verify your integrations for you

Tool status is a factual operational state, not an intention, and the values are ordered and
distinct:

`not_configured` → `configured` → `connected` → `tested` → `production_approved`

**Every integration in this package ships `not_configured`.** A YAML entry, a package file or a
documentation page is not evidence that anything is connected. If the skill cannot verify a tool, it
must return a manual procedure or a draft integration contract and say so — never numbers that look
like they came from a system nobody queried. That is tested as T07.

## Do not put real client data in this repository

The skill writes project state to `<workspace>/.rebuild/`. That directory contains the client's
numbers, decisions, evidence and open questions. `.gitignore` excludes it, and it should stay out of
version control.

If you want to publish a worked example, anonymise it: change the names, round the figures so they
cannot be reverse-identified, and label every number as given or assumed. The example in
`examples/bonded-apartment-intake/` follows that rule and says so at the top of the file.

## Evidence discipline is an integrity control, not a style rule

The `FACT` / `INTERPRETATION` / `HYPOTHESIS` / `DECISION` / `UNKNOWN` labels and the A–E source
grades exist so a reader can tell what was verified from what was assumed. Marking an assumption as
a fact is the most damaging thing this skill can do, because the output is designed to be acted on
and reads as authoritative either way.

In particular:

- A market size without geography, category, period and method is not a market size.
- A case study is not causal evidence for your project.
- A trend is not an opportunity until you state the mechanism that connects them.
- A platform-attributed conversion is not proof of incremental lift.
- Averages of conflicting claims are not a resolution. Preserve the disagreement.

## Reporting a problem

If you find a path by which the skill can be induced to spend money, contact customers, publish, or
fabricate evidence presented as fact, please open an issue with the prompt and the output. Those are
the reports we most want, and they will be treated as defects rather than as user error.

## Licence and liability

MIT (`LICENSE`). The skill produces strategic advice for human decision-makers. It does not replace
legal, financial, tax, or regulatory advice, and its output is not a professional opinion. You remain
responsible for the decisions you take and for the external actions you authorise.

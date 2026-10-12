# Quality Gates, Risk and Stop Conditions

## Gate statuses
- `PASS`: exit criteria met.
- `PASS_WITH_GAPS`: continue only with named limitations, owner and mitigation.
- `BLOCKED`: a decision-critical gap makes the next phase unsafe or wasteful.

## R gate — problem and contract
Pass when business decision, scope, stakeholder, constraints, baseline and success criteria are sufficiently explicit. Block if the requested output cannot be connected to any decision or success criterion.

## E gate — evidence and opportunity
Pass when decision-critical questions have relevant evidence or a consciously accepted test plan. Block unsupported claims that could materially alter the decision.

## B gate — strategic choice
Pass when target, promise, economics, capabilities, trade-offs and rejected options are explicit. Block when options are not genuinely distinct or the selected option violates a known constraint.

## U gate — strategy-to-creative translation
Pass when creative/content expresses the chosen strategy, is audience-relevant, has proof and a desired action. Block slogan-only responses that do not change product, message or behavior.

## I gate — execution readiness
Pass when owners, timing, budget, channel roles, event tracking, CRM/sales handoff, approval rights, risks and stop rules are defined. Block external actions without authorization.

## D gate — learning and decision
Pass when actual vs expected results, data limitations and next decision are recorded. Decide `scale / iterate / pivot / pause / stop`; do not call a result successful just because activity completed.

## Red Team checklist
Attack from:
1. Customer: Is the need real, urgent and evidenced?
2. Competition: Can incumbents copy this? Are substitutes overlooked?
3. Business: Does the model create durable value and revenue?
4. Finance: Does contribution work after real costs and payback?
5. Execution: Can the team, time and channels deliver?
6. Organization: Who can veto, and do incentives conflict?
7. Technology/data: Are systems, permissions and data reliable?
8. Measurement: Could attribution, seasonality or selection bias explain results?
9. Reputation/legal: Are claims, privacy and category constraints acceptable?

## Stop conditions
Stop and request clarification/evidence if:
- critical source data is missing or contradictory;
- unit economics are structurally negative with no plausible testable route to repair;
- proposed action is outside granted authority;
- required privacy/legal/security controls are absent;
- the requested success claim exceeds available evidence;
- a live tool status is unknown but the task assumes it is connected.

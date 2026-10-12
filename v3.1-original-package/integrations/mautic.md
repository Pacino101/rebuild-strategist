# mautic

Intended role: Marketing automation: draft campaigns only until explicit approval; outbound messaging requires consent and review.

Status: `not_configured` until verified in the target environment.

Acceptance test:
1. Confirm exact service and supported connection method.
2. Connect with least-privilege credentials stored outside this repository.
3. Run one read-only/sample test where possible.
4. Save sanitized evidence of response, timestamp and permission scope.
5. Test failure handling and rate-limit behavior.
6. Update `config/tool-registry.yaml` only after the relevant status transition is evidenced.

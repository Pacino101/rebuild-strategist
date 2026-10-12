# Security Policy

## Supported Versions

This project is at the methodology and tooling framework stage; only the latest main branch version is maintained.

| Version | Supported |
|---------|-----------|
| `main` | ✅ |
| Historical commits < `main` | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability, or content in this repository involves third-party information that should not be public (client privacy, unauthorised data, secrets, personal information), please report it privately through GitHub's **Security → Report a vulnerability**, and do not file a public Issue.

Please state in your report:

1. The specific file and location of the problem
2. How to reproduce it or the trigger conditions
3. The potential impact
4. The fix direction you suggest (if any)

We will do our best to acknowledge receipt and respond within 7 days.

## Material involving real projects

When submitting cases, research data or benchmark results to this repository, please follow the rules in `CONTRIBUTING.md`: do not submit client privacy, secrets or unauthorised business data. Material from real projects must be anonymised, and its real / synthetic / anonymised nature clearly marked.

## What this project does not collect

REBUILD does not connect to any marketing data platform, does not collect user behaviour data, and contains no telemetry, tracking or analytics scripts. The repository itself will not send your project content back to any server.

**But this project is not entirely offline; earlier versions of this statement were wrong.** `bench/provider.py` is an optional model access layer (introduced in V3.2.2). When you explicitly specify `--provider`, it makes HTTP requests to the model API endpoint you choose, and sends the prompt content there.

- **Off by default**: when `--provider` is not specified, no network request is made, and manual mode is used (render the prompt → paste it yourself → retrieve the output).
- **The endpoint is your decision**: it can be the official API, a self-hosted proxy or a local Ollama. Keys are read from environment variables only, and are not written to disk or into the repository.
- **Content leaves your machine**: once invoked, the prompt content is sent to that endpoint. If it involves client material or trade secrets, use manual mode or a local model instead.
- **The repository contains no credentials**: `.gitignore` excludes `.env`, and the code does not hard-code any key.

If your compliance requirements are full offline operation, use manual mode throughout, and do not use `--provider`.

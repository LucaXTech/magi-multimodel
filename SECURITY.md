# Security and data handling

## API keys

Store provider credentials only in `.env`. The repository `.gitignore` excludes `.env`, but always inspect staged files before pushing:

```bash
git status
git diff --cached
```

If a secret is ever committed, treat it as compromised: revoke/rotate it at the provider and remove it from Git history before publishing.

## Biomedical and personal data

MAGI and BioAudit send prompts to configured external model providers. Do not submit identifiable patient information, protected health information, confidential research data, credentials, or proprietary documents unless you have an appropriate lawful basis, authorization, and provider/data-processing configuration.

Use synthetic or de-identified examples for public demos.

## Generated results

Runtime outputs are excluded from Git by default (`runs/`, benchmark result directories, and BioAudit result directories). Review any artifact manually before publishing it because model outputs can reproduce sensitive input text.

## Reporting vulnerabilities

For now, report security issues privately to the repository owner rather than opening a public issue containing secrets or sensitive data.

# Security Policy

We take security seriously and value your efforts to help us identify and fix vulnerabilities in the appstore project.

## Reporting a Vulnerability

Please report security vulnerabilities responsibly by emailing:

```
[INSERT SECURITY CONTACT EMAIL, e.g., security@yourdomain.com]
```

Do **not** create a public GitHub issue, discussion, or pull request for security concerns.

## What We Accept

We encourage responsible disclosure of:

- Vulnerabilities in the codebase (Docker configurations, Python services, APIs).
- Issues in deployment setups (Nginx reverse proxy, container orchestration).
- Security misconfigurations that could affect production environments.

## Disclosure Process

1. **Submit your report**: Email a detailed description including reproduction steps, impact, and affected versions.
2. **Acknowledgment**: We'll confirm receipt within 48 hours.
3. **Assessment**: Our team will triage and validate the issue.
4. **Resolution**: We'll work on a fix and keep you updated on progress.
5. **Release**: We'll publish a patch and credit you (with your permission) in the release notes.
6. **Disclosure**: After the fix is released, we'll coordinate public disclosure.

## Timeline Goals

- **Initial response**: 48 hours
- **Fix availability**: 7-14 days (depending on severity)
- **Public disclosure**: 90 days or when the fix is available, whichever is sooner

## Preferred Disclosure Format

Include:

```
Title: [Brief summary]
Version: [Affected version(s)]
Severity: [CVSS score if known, or Low/Medium/High]
Description: [Detailed explanation]
Steps to reproduce: [Clear, numbered steps]
Impact: [Business/security impact]
Proof of concept: [Code/link if available]
Environment: [Docker version, Ubuntu version, etc.]
```

## Rewards

We don't currently offer a formal bug bounty, but significant contributions may earn recognition or swag.

## Legal Safe Harbor

Any good faith disclosure following this policy grants safe harbor from legal action.

Thank you for helping keep appstore secure!

***

Add this as `SECURITY.md` in your repo root. Replace `[INSERT SECURITY CONTACT EMAIL]` with your preferred contact (e.g., a dedicated security alias). GitHub will automatically detect and link it in issues.

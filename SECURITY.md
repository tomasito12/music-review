# Security Policy

## Supported versions

Security fixes are applied on the default branch (`main`) and released through
normal development. There is no separate long-term support branch.

| Version | Supported |
| ------- | --------- |
| latest on `main` | yes |
| older tags or forks | best effort |

## Reporting a vulnerability

If you discover a security vulnerability, please report it privately rather than
opening a public GitHub issue.

**Preferred contact:** open a
[GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
("Report a vulnerability" on the repository Security tab), or email the
repository owner via the contact address on their GitHub profile.

Include as much of the following as you can:

- Description of the issue and potential impact
- Steps to reproduce or a proof of concept
- Affected components (API, Streamlit app, scraper, deployment, CI, etc.)
- Suggested fix or mitigation, if you have one

We aim to acknowledge reports within a few business days and will keep you
informed about progress.

## Scope

In scope examples:

- Authentication or session handling flaws in the API or dashboard
- Injection, SSRF, or unsafe deserialization in application code
- Exposure of secrets, credentials, or private user data through the app or CI
- Container or deployment misconfigurations documented in this repository

Out of scope examples:

- Issues in third-party services (MusicBrainz, plattentests.de, OpenAI, GitHub)
- Social engineering or physical attacks
- Denial-of-service against external sites scraped by the pipeline
- Vulnerabilities in dependencies with no practical exploit path in this project

Dependency updates are handled through normal development and CI; report
critical CVEs with exploit details if you believe the project is affected.

## Safe disclosure

Please allow reasonable time to investigate and patch before public disclosure.
We appreciate responsible disclosure and will credit reporters when fixes are
published, unless you prefer to remain anonymous.

## Code of conduct reports

Reports related to the [Code of Conduct](CODE_OF_CONDUCT.md) may use the same
private contact channels above.

## Operational security notes for contributors

- Never commit `.env`, production SSH keys, or API tokens.
- Treat `data/` as sensitive when it contains production databases or scraped
  content synced from a private deployment.
- Rotate credentials if they were accidentally committed or logged.

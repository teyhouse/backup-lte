# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please open a
[private security advisory](https://github.com/teyhouse/backup-lte/security/advisories/new)
or contact the maintainer directly. Please do not open a public issue for
security problems.

You can expect a response within 7 days.

## Scope

This bot runs with a Discord bot token and scrapes `pass.telekom.de`. Areas
of interest include:

- Token or credential leakage (the `.env` file must never be committed)
- Unauthorized use of the `/lte` command
- Injection via scraped HTML content

## Supported Versions

| Version | Supported |
|---------|-----------|
| main    | ✅        |

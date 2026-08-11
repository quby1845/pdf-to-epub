# Security Policy

## Supported versions

Security fixes are provided for the latest released minor version.

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| Earlier / unreleased snapshots | No |

## Reporting a vulnerability

Do not disclose a suspected vulnerability in a public issue, discussion, or pull request.

Use **Security → Report a vulnerability** on the GitHub repository when private vulnerability
reporting is available. Include:

- affected version and platform;
- impact and realistic attack scenario;
- minimal reproduction steps or proof of concept;
- any suggested mitigation.

If the private reporting button is unavailable, open a public issue containing no vulnerability
details and ask the maintainer to establish a private contact channel.

The maintainer aims to acknowledge reports within 7 days and provide an initial assessment within
14 days. Timelines may vary with severity and dependency coordination. Confirmed issues will be
handled privately until a fix and disclosure plan are ready.

## Scope notes

This project processes untrusted PDF input through several third-party tools and model libraries.
Run it with ordinary user privileges, keep dependencies updated, and avoid converting untrusted
documents on systems containing sensitive data. Model downloads and dependency installation use
external package/model hosts even though document contents are processed locally.

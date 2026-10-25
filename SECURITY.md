# Security policy

This project installs mods: archives written by third parties that the tool reads and applies to
a user's game directory. Treating mods as untrusted input is a core design principle, described
in [docs/architecture/THREAT_MODEL.md](docs/architecture/THREAT_MODEL.md).

## Supported versions

The project is in initial development (`0.y.z`). Security fixes are released only for the latest
published release; upgrade to it before reporting.

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Any older release | No |

## Reporting a vulnerability

**Do not open a public issue, discussion or pull request for a vulnerability.**

Report it privately through GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability):
open the repository's **Security** tab and choose **Report a vulnerability**. If that button is
not available, open a public issue that says only that you have a security report and asks a
maintainer for a private channel, without any details.

Please include the affected version (`iemod --version`), your operating system, a description of
the impact, and the smallest mod or command that reproduces it.

## What to expect

- Maintainers are volunteers; there is no guaranteed response time, but reports are prioritised
  over other work.
- You will be told whether the report is accepted. Accepted issues are fixed in a new release
  and disclosed through a GitHub Security Advisory that credits you unless you prefer otherwise.
- Declined reports receive an explanation, typically because the behaviour is within the
  documented trust boundaries of the threat model.

## Scope

In scope: anything that lets a mod or crafted game file read or write outside the selected game
directory, delete files, execute programs, access the network, crash the tool in a way that
corrupts game data, or tamper with release artifacts and the build pipeline.
Out of scope: issues that require an attacker who already controls the user's account or
machine, and vulnerabilities in the games themselves.

"""Shared, dependency-free building blocks for the repository's release automation.

The package is imported by the command-line entry points that live directly under ``scripts/``
(``check_commits.py``, ``release.py``, ``changelog.py``). It deliberately uses only the Python
standard library (3.11+) so that it runs identically on a contributor's machine and on a bare
GitHub-hosted runner without any ``pip install`` step, which keeps CI fast and the supply chain
small.
"""

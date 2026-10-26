# Swarm Witness

A private research hackathon project comparing multi-agent oversight policies
against an external oracle using paired experiments.

## Current status

This repository contains the initial project scaffold.
The research protocol, scenarios, agents, monitors, experiments, and paper are
still to be implemented. This repository remains private.

## Repository layout

| Directory | Purpose |
| --- | --- |
| `protocol/` | Experiment protocol and oversight policy definitions |
| `scenarios/` | Evaluation scenarios and expected outcomes |
| `agents/` | Agent implementations |
| `monitors/` | Oversight and monitoring implementations |
| `analysis/` | Measurements and paired experimental analysis |
| `paper/` | Research write-up |

## Get started

```sh
git clone https://github.com/instagrim-dev/swarm-witness.git
cd swarm-witness
```

Cloning this private repository requires GitHub access.

There are no experiment dependencies or runnable experiments yet.

## Continuous integration

The `validate-scaffold` job in `.github/workflows/ci.yml` runs on pushes,
pull requests, and manual dispatch. It checks that the README and MIT license
are present and nonempty, and that the scaffold directories exist. It uses a
GitHub-hosted Ubuntu runner with read-only repository access and requires no
project secrets.

Run the same checks locally from the repository root:

```sh
set -eu
test -s README.md
test -s LICENSE
grep -qx 'MIT License' LICENSE
for directory in protocol scenarios agents monitors analysis paper; do
  test -d "$directory"
done
printf 'Scaffold checks passed.\n'
```

These checks validate repository setup. Implementation and evaluation checks
will be added as the project develops.

## License

[MIT](LICENSE). Copyright (c) 2026 Jon M.

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

Local validation is the primary check path. Hosted GitHub CI is unavailable
under the project cost policy; the retained Actions workflow is manual-only and
does not run automatically on pushes or pull requests.

Run from the repository root:

```sh
sh scripts/check.sh
```

The command checks the README, MIT license, and scaffold directories without
network access or project secrets. The optional manual workflow runs this same
script; it is not required for local readiness.

These checks validate repository setup. Implementation and evaluation checks
will be added as the project develops.

## License

[MIT](LICENSE). Copyright (c) 2026 Jon M.

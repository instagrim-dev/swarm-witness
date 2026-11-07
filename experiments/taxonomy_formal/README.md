# Taxonomy formalization (issue #12)

Independent formal epistemics and finite-model checks for the Swarm Witness
three-way conclusion discipline.

## Run

```bash
python experiments/taxonomy_formal/run.py
python experiments/taxonomy_formal/run.py --json
pytest -q tests/test_formal_epistemics.py
```

## Oracle independence

The formal model lives in `src/swarm_witness/formal/` and does **not** import
`swarm_witness.conclusion_classes`. Core invariants are checked by enumerating a
finite permission world set; production classifiers are compared only in optional
consistency tests.

## Research note

`analysis/taxonomy_formalization/RESEARCH_NOTE.md`

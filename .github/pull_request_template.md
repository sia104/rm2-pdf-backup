## Summary

## Issue

Closes #

## Type of change

- [ ] Local-only code/test change
- [ ] GitHub Actions/cloud CI change
- [ ] RPI/self-hosted runner change
- [ ] RM2 read-only access change
- [ ] Rendering change
- [ ] Publishing/validation change
- [ ] Documentation only

## Safety checklist

- [ ] Does not write to the RM2
- [ ] Does not delete or modify RM2 files
- [ ] Does not touch the beamline/production RM2
- [ ] Does not commit real RM2 data, generated PDFs, logs, databases, SSH keys, IP addresses or secrets
- [ ] Failed rendering cannot replace previous good PDFs
- [ ] Deletion/archive behaviour is unchanged or explicitly tested

## Tests run

- [ ] `ruff check .`
- [ ] `pytest`
- [ ] Cloud CI
- [ ] RPI dev run-local workflow
- [ ] RPI dev raw-copy workflow
- [ ] Renderer/template probe

## RPI / RM2 validation

Required?

- [ ] No
- [ ] Yes

Result / workflow URL:

## Risk level

- [ ] Low
- [ ] Medium
- [ ] High

## Remaining limitations

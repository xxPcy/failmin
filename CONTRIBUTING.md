# Contributing to FailMin

Thanks for helping improve FailMin. The project is intentionally framework-neutral: core reduction logic should not depend directly on a specific Agent framework.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
pytest
```

## Contribution guidelines

- Keep core algorithms framework-agnostic.
- Put framework-specific parsing/replay logic under `failmin/adapters/`.
- Add tests for behavior changes and bug fixes.
- Preserve dependency-valid traces during reduction.
- Avoid introducing network requirements into the zero-config demo.
- Keep public API changes backward compatible where practical.

## Good first contributions

- New Generic JSON fixtures.
- Trace schema validation improvements.
- Framework adapters.
- Report UX improvements.
- Reproduction strategies for flaky/non-deterministic agents.

## Pull requests

Please explain the failure scenario, the expected behavior, and how you tested the change. Small, focused pull requests are easier to review.

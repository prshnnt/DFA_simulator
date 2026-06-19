# Contributing

Thanks for your interest in improving the DFA Visual Simulator. This project
is intentionally small and single-file, so contributions are easy to land.

## Development setup

The project uses [`uv`](https://docs.astral.sh/uv/), but plain `pip` works
just as well.

```bash
# Clone and enter
git clone <repository-url>
cd DFA_simulator

# Install runtime + dev dependencies
uv sync --extra dev

# Run the simulator
uv run python main.py

# Run the tests
uv run pytest
```

## Code style

- **Python 3.12+** syntax (PEP 604 unions, `match` statements where useful).
- Type hints on all public functions and methods.
- Docstrings on every module, class, and non-trivial function — keep them
  short and focused on *why*, not *what*.
- Avoid single-letter variable names except for short-lived loop indices.
- Prefer the standard library over new third-party dependencies.

## Layout conventions

- The whole app lives in `main.py`. Keep it that way unless there is a strong
  reason to split.
- Pure logic (no pygame dependency) belongs in `DFA`, `SimState`, or `Animator`
  and must remain unit-testable without a display.
- New tests go under `tests/` and follow the existing `test_<module>.py` name.

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/).

| Prefix      | When                                                |
|-------------|-----------------------------------------------------|
| `feat:`     | A user-visible feature                              |
| `fix:`      | A bug fix                                           |
| `docs:`     | Documentation only                                  |
| `refactor:` | Internal change with no behaviour difference        |
| `test:`     | Adding or fixing tests                              |
| `build:`    | Build, packaging, or tooling changes                |
| `chore:`    | Maintenance tasks that don't fit above              |

Subject line: 50 characters or fewer, imperative mood, no trailing period.

## Pull request checklist

- [ ] Tests pass: `uv run pytest`
- [ ] New behaviour has a test
- [ ] Public API additions have docstrings
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] No editor / OS-specific junk in the diff

## Reporting bugs

Open an issue with:

1. Operating system and Python version
2. Steps to reproduce
3. Expected vs. actual behaviour
4. Screenshot or screen recording if it's a visual issue
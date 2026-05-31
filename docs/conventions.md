# Conventions

## Project Structure

```
src/
├── adapters/       # External systems: database, browser, email, crypto
├── interfaces/     # GUI: windows, views, styles
├── models/         # Data classes and shared helpers
└── usecases/       # Business logic: execution, recording, reading/writing
data/               # Database and encryption key (not committed)
docs/               # Documentation
```

## Python-Conventions

Follows [PEP 8](https://peps.python.org/pep-0008/).

## Git-Conventions

Commit format: `<type>: <short description>` in lowercase, no trailing period.

| Type | Use |
|------|-----|
| `feat` | new feature |
| `fix` | bug fix |
| `refactor` | restructuring without behaviour change |
| `style` | formatting, no logic impact |
| `docs` | documentation |
| `chore` | build, dependencies, configuration |


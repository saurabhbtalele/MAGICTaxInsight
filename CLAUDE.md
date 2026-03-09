# CLAUDE.md

## Build & Test Commands (Docker Only)

- **Build Image**: `.\run.bat build` (Windows) / `make build` (Unix)
- **Run Tests**: `.\run.bat test` (Windows) / `make test` (Unix)
- **Interactive Shell**: `.\run.bat shell` (Windows) / `make shell` (Unix) - _Use this for all debugging_
- **Run Parser**: `.\run.bat run <pdf>` (Windows) / `make run <pdf>` (Unix)
- **Batch Mode**: `.\run.bat batch <dir>` (Windows) / `make batch <dir>` (Unix)

## Code Style

- **Engine**: 3-Tier (Docling -> Gemini -> local)
- **Imports**: Avoid circular dependencies between `src/` modules
- **Types**: Use Python type hints where possible
- **Documentation**: Keep `DESIGN.md` and `README.md` updated for major changes

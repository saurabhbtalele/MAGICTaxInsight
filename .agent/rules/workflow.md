# Project Workflow Rules

Follow these rules for a consistent development lifecycle:

## 1. Development Cycle

1. **Modify**: Implement features or fixes in `src/`.
2. **Build**: Run `.\run.bat build` (Windows) or `make build` (Unix) to refresh the Docker environment.
3. **Debug/Test**: Run `.\run.bat test` (Windows) or `make test` (Unix) inside Docker.
4. **Shell Debug**: Use `.\run.bat shell` or `make shell` to enter the container for interactive debugging/running `debug_*.py` scripts.
5. **Run**: Verify final output with `.\run.bat run <pdf_path>` or `make run <pdf_path>`.

## 2. Docker-Only Workflow

- **No Local Environment**: All dependencies (Tesseract, PaddleOCR, etc.) are managed within Docker. Do not attempt a local `pip install`.
- **Image Refresh**: Always build after changing `requirements.txt` or `Dockerfile`.
- **Interactive Debugging**: Use the `shell` command to run scripts inside the container for line-by-line or script-based debugging.

## 2. Coding Standards

- Use Python 3.10+ features.
- Follow existing patterns in `src/document_parser.py` for new parsers.
- Maintain the 3-Tier extraction architecture (Docling -> LLM -> Regex/Plumber).

## 3. Docker Usage

- Always build after changing `requirements.txt` or `Dockerfile`.
- Use the provided `make shell` or `.\run.bat shell` for internal container debugging.

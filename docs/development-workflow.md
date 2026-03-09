# Development Workflow

Magic Tax Insight is built with developer experience, cross-platform portability, and powerful observability in mind.

## 1. Running the System Locally

Because of the high dependency requirements (like `libgl1`, `Tesseract-OCR`, and `Python 3.10` features), the application is fully Dockerized. This ensures zero "it works on my machine" issues.

### Using the Script Runners

We provide standard script runners to abstract away messy Docker commands.

**If you are on Windows:**
Open PowerShell/CMD.

```bash
# Build the Docker environment
.\run.bat build

# Run the parser on a test file
.\run.bat run samples/document.pdf

# Run an entire folder of PDFs using Batch mode
.\run.bat batch samples/

# Run the full unit testing suite
.\run.bat test

# Open an interactive shell inside the container to debug
.\run.bat shell
```

**If you are on Mac/Linux:**

```bash
# Build the environment
make build              # OR ./run.sh build

# Run the parser on a single file
make run samples/document.pdf    # OR ./run.sh run samples/document.pdf

# Run the parser on a batch directory
make batch samples/              # OR ./run.sh batch samples/

# Run tests
make test                        # OR ./run.sh test
```

## 2. Environment Variables (.env)

The extraction engine can operate 100% locally. However, if a document requires the **Tier 2 LLM fallback**, it needs an API key.

1. Copy `.env.example` to `.env`
2. Add your Gemini API key:

```env
GEMINI_API_KEY="your_api_key_here"
```

Because the system runs in Docker, it automatically loads `.env` and passes it to the container.

## 3. Understanding Your Output

Once the parser has analyzed the provided PDF, it outputs directly to the `output/` directory, which is volume-mounted from the container to your host machine.

- **Result JSON**: `output/tax_poc_result.json` will contain your field-extracted form values.

## 3. Advanced Logging with Loguru

Standard `print()` statements are notoriously difficult to track in Dockerized enterprise production apps. We use **Loguru**.

When running the project, you will notice:

- **Beautiful Colors**: Your command line will display fully colorized logs indicating exactly what function and line failed.
- **Persistent Rotating Log Files**: Inside `output/logs/`, you will see files named `app_2026-XX-YY_XX-XX.json`. Let them pile up. Loguru will completely automatically manage them. Every time they reach 10 MB, it zips them up and handles rotation (deleting logs older than 5 days). This is extremely handy when uploading logs to Datadog or ELK.
- **Exception Diagnostics**: If code fails, Loguru will catch the exception and print the _exact_ variables holding the runtime state so you don't even need a breakpoint debugger.

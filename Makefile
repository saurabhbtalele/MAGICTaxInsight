.PHONY: help build run shell clean

# Default target when just typing 'make'
help:
	@echo "Available commands (Python's package.json equivalent):"
	@echo "  make build    - Build the Docker image"
	@echo "  make run [f]  - Run the parser on a single PDF (e.g. samples/my_file.pdf)"
	@echo "  make batch [d]- Run the parser on a directory of PDFs (e.g. samples/)"
	@echo "  make test     - Run the full unit test suite inside Docker"
	@echo "  make shell    - Open a bash shell inside the Docker container for debugging"
	@echo "  make clean    - Clean up python cache files and clear the output directory"

build:
	docker-compose build

# Allow passing arguments to make run (e.g. make run samples/my_file.pdf)
# We capture everything after 'run' and turn them into arguments
RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
$(eval $(RUN_ARGS):;@:)

run:
	@if [ -z "$(RUN_ARGS)" ]; then \
		echo "Usage: make run [path/to/pdf]"; \
		echo "Example: make run samples/document.pdf"; \
		echo ""; \
		echo "Running with default: samples/document.pdf"; \
		docker-compose run --rm app samples/document.pdf; \
	else \
		docker-compose run --rm app $(RUN_ARGS); \
	fi

batch:
	@if [ -z "$(RUN_ARGS)" ]; then \
		echo "Usage: make batch [path/to/dir]"; \
		echo "Example: make batch samples/"; \
		echo ""; \
		echo "Running with default: samples/"; \
		docker-compose run --rm --entrypoint "python -m src.batch_processor samples/" app; \
	else \
		docker-compose run --rm --entrypoint "python -m src.batch_processor $(RUN_ARGS)" app; \
	fi

test:
	docker-compose run --rm --entrypoint "python -m pytest" app

shell:
	docker-compose run --rm --entrypoint /bin/bash app

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

#!/usr/bin/env bash

# Cross-platform script runner for Mac/Linux

case "$1" in
    help|"")
        echo "Available commands:"
        echo "  ./run.sh build    - Build the Docker image"
        echo "  ./run.sh run [file]- Run the parser on a single PDF (e.g. samples/my_file.pdf)"
        echo "  ./run.sh batch [dir]- Run the parser on a directory of PDFs (e.g. samples/)"
        echo "  ./run.sh test     - Run the full unit test suite inside Docker"
        echo "  ./run.sh shell    - Open a bash shell inside the Docker container for debugging"
        echo "  ./run.sh clean    - Clean up python cache files and clear the output directory"
        ;;
    build)
        docker-compose build
        ;;
    run)
        if [ -z "$2" ]; then
            echo "Usage: ./run.sh run [path/to/pdf]"
            echo "Example: ./run.sh run samples/document.pdf"
            echo ""
            echo "Running with default: samples/document.pdf"
            docker-compose run --rm app samples/document.pdf
        else
            docker-compose run --rm app "$2"
        fi
        ;;
    batch)
        if [ -z "$2" ]; then
            echo "Usage: ./run.sh batch [path/to/dir]"
            echo "Example: ./run.sh batch samples/"
            echo ""
            echo "Running with default: samples/"
            docker-compose run --rm --entrypoint "python -m src.batch_processor samples/" app
        else
            docker-compose run --rm --entrypoint "python -m src.batch_processor $2" app
        fi
        ;;
    test)
        docker-compose run --rm --entrypoint "python -m pytest" app
        ;;
    shell)
        docker-compose run --rm --entrypoint /bin/bash app
        ;;
    clean)
        find . -type d -name __pycache__ -exec rm -rf {} +
        find . -type f -name "*.pyc" -delete
        echo "Cleaned up python caches."
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        $0 help
        ;;
esac

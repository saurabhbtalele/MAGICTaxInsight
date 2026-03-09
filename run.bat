@echo off
setlocal

:: Cross-platform script runner for Windows

if "%1"=="help" goto help
if "%1"=="" goto help
if "%1"=="build" goto build
if "%1"=="run" goto run
if "%1"=="batch" goto batch
if "%1"=="test" goto test
if "%1"=="shell" goto shell
if "%1"=="clean" goto clean

echo Unknown command: %1
echo.
goto help

:help
echo Available commands:
echo   .\run.bat build    - Build the Docker image
echo   .\run.bat run [file]- Run the parser on a single PDF (e.g. samples/my_file.pdf)
echo   .\run.bat batch [dir]- Run the parser on a directory of PDFs (e.g. samples/)
echo   .\run.bat test     - Run the full unit test suite inside Docker
echo   .\run.bat shell    - Open a bash shell inside the Docker container for debugging
echo   .\run.bat clean    - Clean up python cache files and clear the output directory
goto end

:build
docker-compose build
goto end

:run
if "%2"=="" (
    echo Usage: .\run.bat run [path/to/pdf]
    echo Example: .\run.bat run samples/document.pdf
    echo.
    echo Running with default: samples/document.pdf
    docker-compose run --rm app samples/document.pdf
) else (
    docker-compose run --rm app %2
)
goto end

:batch
if "%2"=="" (
    echo Usage: .\run.bat batch [path/to/dir]
    echo Example: .\run.bat batch samples/
    echo.
    echo Running with default: samples/
    docker-compose run --rm --entrypoint "python -m src.batch_processor samples/" app
) else (
    docker-compose run --rm --entrypoint "python -m src.batch_processor %2" app
)
goto end

:test
docker-compose run --rm --entrypoint "python -m pytest" app
goto end

:shell
docker-compose run --rm --entrypoint /bin/bash app
goto end

:clean
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>&1
echo Cleaned up python caches.
goto end

:end
endlocal

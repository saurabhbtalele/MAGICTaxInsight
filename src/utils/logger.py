import sys
from pathlib import Path
from loguru import logger

def configure_logger():
    """
    Configures a best-in-class logger for the application using Loguru.
    Features:
      - Colorized console output for beautiful local debugging
      - Rotating JSON logs inside the mounted 'output/logs' directory for portability
      - Preserves stack traces and handles exceptions perfectly
      - Rotation set to 10 MB per file, keeping only the last 5 files to preserve memory
    """
    # Remove default handler
    logger.remove()

    # 1. Console Handler: Beautiful, colorized sink for the developer
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        level="DEBUG",
        enqueue=True, # Thread-safe
    )

    # 2. File Handler: JSON formatted, rotating logs inside the mounted 'output' dir
    # Ensures logs are fully preserved and easily parseable by tools like Datadog, ELK, Splunk
    log_dir = Path("output/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_dir / "app_{time}.json",
        format="{message}",
        level="INFO",
        serialize=True,     # Outputs as pure JSON
        rotation="10 MB",   # Rotate when file reaches 10MB
        retention="5 days", # Keep logs for 5 days
        compression="zip",  # Compress old logs to save space
        enqueue=True,       # Thread-safe
        backtrace=True,     # Capture full backtrace 
        diagnose=True       # Keep variables context in errors (extremely helpful)
    )
    
    return logger

# Export the configured logger instance
log = configure_logger()

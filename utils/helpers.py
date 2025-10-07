"""
Helper utilities for the Sales Automation Agent
"""

import logging
import os


def setup_api_logger():
    """Setup logger for API interactions"""
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Create a logger for API interactions
    api_logger = logging.getLogger("api_interactions")
    api_logger.setLevel(logging.DEBUG)

    # Create file handler
    file_handler = logging.FileHandler("logs/api_interactions.log")
    file_handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add handler to logger if it doesn't already have it
    if not api_logger.handlers:
        api_logger.addHandler(file_handler)

    return api_logger

import logging

def setup_logger():
    """Configure logging for the application."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set root logger to DEBUG

    # Create console handler with a higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s', 
                                datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(console_handler)

    return logger

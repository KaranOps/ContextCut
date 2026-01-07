import logging
import sys

def setup_logger():
    logger = logging.getLogger("ContextCut")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    return logger

logger = setup_logger()

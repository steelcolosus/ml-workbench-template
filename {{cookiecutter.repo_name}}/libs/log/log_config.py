import logging
import logging.config

_configured = False


def get_logger(name):
    # Configure logging once per process, not on every call
    global _configured
    if not _configured:
        logging.config.dictConfig(get_log_config())
        _configured = True
    return logging.getLogger(name)


def get_log_config():
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {"format": "%(asctime)s [%(levelname)s][%(name)s] %(message)s"}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "": {"level": logging.INFO, "handlers": ["console"], "propagate": True}
        },
    }

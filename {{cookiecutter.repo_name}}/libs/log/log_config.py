import logging
import logging.config


def get_logger(name):
    logging.config.dictConfig(get_log_config())
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

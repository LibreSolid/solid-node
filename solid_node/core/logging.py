import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)15s - %(message)s'
)

uvicorn_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "access": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelname)s - %(name)15s - %(message)s",
            "use_colors": True,
        },
    },
    "handlers": {
        "default": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}

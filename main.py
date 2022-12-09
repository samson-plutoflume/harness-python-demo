import logging
import os
import time

from featureflags.client import CfClient
from featureflags.config import (
    with_base_url,
    with_events_url,
    with_stream_enabled,
    with_analytics_enabled,
    Config,
)
from featureflags.evaluations.auth_target import Target
from featureflags.util import log
from structlog import get_logger
import structlog

log.setLevel(logging.INFO)
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = get_logger(__name__)
logger.info("Started Harness Demo")


API_KEY = os.environ["HARNESS_API_KEY"]
BASE_URL = os.environ["HARNESS_BASE_URL"]
EVENT_URL = os.environ["HARNESS_EVENT_URL"]
POLLING_INTERVAL = int(os.environ["HARNESS_POLL_INTERVAL"])

TARGETS = [
    (1, "southerton"),
    (2, "grove"),
    (3, "finsbury"),
    (4, "canada"),
    (5, "featherstone"),
]
FLAGS = [("doors_enabled", "bool", False), ("capacity", "int", 1)]


def main():
    logger.info("Creating client", base_url=BASE_URL, events_url=EVENT_URL)
    client = CfClient(
        API_KEY,
        with_base_url(BASE_URL),
        with_events_url(EVENT_URL),
        with_stream_enabled(True),
        with_analytics_enabled(True),
        config=Config(pull_interval=POLLING_INTERVAL),
    )

    targets = [
        Target(
            identifier=str(i),
            name=name,
            attributes={
                "location": "emea" if i % 2 else "asia"
            }
        ) for i, name in TARGETS]
    flag_settings = {(flag, target): flag_default for flag, _, flag_default in FLAGS for target, _ in TARGETS}

    with client:
        while True:
            logger.info("Re-requesting all flags")
            for target in targets:
                for flag, flag_type, flag_default in FLAGS:
                    if flag_type == "bool":
                        result = client.bool_variation(flag, target, flag_default)
                    elif flag_type == "int":
                        result = client.int_variation(flag, target, flag_default)
                    else:
                        result = client.string_variation(flag, target, flag_default)

                    if result != flag_settings.get((flag, target.identifier)):
                        logger.info(
                            "Flag changed",
                            flag_name=flag,
                            target=target.name,
                            target_id=target.identifier,
                            previous_value=flag_settings.get((flag, target.identifier)),
                            current_value=result,
                            flag_type=str(type(result)),
                        )
                        flag_settings[(flag, target.identifier)] = result
            time.sleep(5)


if __name__ == '__main__':
    main()

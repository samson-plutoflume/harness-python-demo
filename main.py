import logging
import os
import time
from typing import Any, Callable

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
from faker import Faker

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

Faker.seed(123)
faker = Faker()



def get_target(
    tenant_id: int, subdomain: str, is_demo: bool = False, **additional_attributes: Any
) -> Target:
    return Target(
        identifier=str(tenant_id),
        name=str(tenant_id),
        attributes={
            "subdomain": "".join(l for l in subdomain.lower() if "a" <= l <= "z"),
            "is_demo": is_demo,
            **additional_attributes,
        },
    )


TARGETS = [
    *(
        get_target(
            1 + i,
            faker.company(),
            False,
            region="eu-west-1",
            defender_phase=i % 3,
            enforcer_phase=i % 3,
        )
        for i in range(20)
    ),
    *(
        get_target(
            10000 + i,
            faker.company(),
            False,
            region="us-west-2",
            defender_phase=i % 3,
            enforcer_phase=i % 3,
        )
        for i in range(20)
    ),
    *(
        get_target(
            90 + i,
            f"demo{faker.first_name().lower()}",
            True,
            region="eu-west-1",
            test_account=True,
            defender_phase=2,
            enforcer_phase=2,
        )
        for i in range(10)
    ),
    *(
        get_target(
            500 + i,
            faker.company(),
            False,
            region="eu-west-1" if i % 2 else "us-west-2",
            ekm=True,
        )
        for i in range(15)
    ),
]


def get_all_flags(client: CfClient) -> list[tuple[str, Any, Callable]]:
    return [
        ("account_takeover_enabled", False, client.bool_variation),
        ("risk_hub_enabled", False, client.bool_variation),
        ("inbound_queue_service", "kinesis", client.string_variation),
        ("defender_message_generator", "legacy", client.string_variation),
        ("defender_generate_semtex", False, client.bool_variation),
        ("semtex_template_version", 1, client.int_variation),
        ("investigate_and_report_enabled", False, client.bool_variation),
        ("defender_via_api_quarantine", "none", client.string_variation),
    ]


def main():
    logger.info("Initialising targets", subdomains=[t.attributes["subdomain"] for t in TARGETS])

    API_KEY = os.environ["HARNESS_API_KEY"]
    BASE_URL = os.environ["HARNESS_BASE_URL"]
    EVENT_URL = os.environ["HARNESS_EVENT_URL"]
    POLLING_INTERVAL = int(os.environ["HARNESS_POLL_INTERVAL"])
    logger.info("Creating client", base_url=BASE_URL, events_url=EVENT_URL)
    client = CfClient(
        API_KEY,
        with_base_url(BASE_URL),
        with_events_url(EVENT_URL),
        with_stream_enabled(True),
        with_analytics_enabled(True),
        config=Config(pull_interval=POLLING_INTERVAL),
    )

    flags = get_all_flags(client)

    with client:
        while True:
            logger.info("Re-requesting flags", flags=[name for name, *_ in flags])
            for target in TARGETS:
                for flag, flag_default, variation_callable in flags:
                    result = variation_callable(flag, target, flag_default)
                    logger.info(
                        "Found flag",
                        flag_name=flag,
                        flag_value=result,
                        flag_type=str(type(result)),
                        target_id=target.identifier,
                        target_attributes=target.attributes,
                    )
            time.sleep(10)


if __name__ == "__main__":
    main()

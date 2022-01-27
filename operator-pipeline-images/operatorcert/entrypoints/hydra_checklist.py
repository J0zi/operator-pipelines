import argparse
import logging
import sys
from typing import Any, Dict

from operatorcert import hydra
from operatorcert.logger import setup_logger

LOGGER = logging.getLogger("operator-cert")


def setup_argparser() -> Any:  # pragma: no cover
    """
    Setup argument parser

    Returns:
        Any: Initialized argument parser
    """
    parser = argparse.ArgumentParser(description="Hydra checklist cli tool.")

    parser.add_argument(
        "--cert-project-id", help="Certification project ID", required=True
    )
    parser.add_argument(
        "--hydra-url",
        default="https://connect.redhat.com/hydra/prm",
        help="URL to the Hydra API",
    )
    parser.add_argument(
        "--ignore-publishing-checklist",
        default="false",
        help="Ignore the results of the publishing checklist",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def check_single_hydra_checklist(checklist: Dict[str, Any]) -> bool:
    """
    Check a single Hydra checklist and return if it passed and log failed tests

    Args:
        checklist (Dict[str, Any]): Hydra single checklist

    Returns:
        bool: A flag that determines if a all checks in the checklist passed
    """

    checklist_items = checklist["checklistItems"]
    completed = True
    for item in checklist_items:
        completed = completed and item["completed"]
        if not item["completed"]:
            LOGGER.error(
                f"FAILED: Checklist item not completed: {item['title']} - {item['reasons']}"
            )
        else:
            LOGGER.info(f"PASSED: Checklist item completed: {item['title']}")
    return completed


def check_hydra_checklist_status(
    cert_project_id: str, hydra_url: str, ignore_publishing_checklist: bool
) -> None:
    """
    Call Hydra checklist API and check if all test passed

    Args:
        cert_project_id (str): Certification project identifier
        hydra_url (str): Base Hydra API URL
        ignore_publishing_checklist (bool): Set this flag to True to avoid an abrupt
            `sys.exit` with a non-zero status code when there are failed checklist results.
            The failures will still be logged.

    """
    # query hydra checklist API
    # Not using urljoin because for some reason it will eat up the prm at the end if
    # url doesn't end with a /
    hydra_checklist_url = f"{hydra_url}/v2/projects/{cert_project_id}/checklist/status"

    LOGGER.info("Examining pre-certification checklist from Hydra...")
    hydra_resp = hydra.get(hydra_checklist_url)
    if hydra_resp["completed"]:
        LOGGER.info(
            f"Pre-certification checklist is completed for cert project with id "
            f"{cert_project_id}."
        )
        return

    LOGGER.debug("Checklist overall status is incomplete. Checking individual items...")

    # if checklist is not complete, go through each item and log which ones are missing
    checklists = hydra_resp.get("checklists", [])

    completed = True
    for checklist in checklists:
        completed = completed and check_single_hydra_checklist(checklist)
    if not completed:
        LOGGER.info(
            f"Pre-certification checklist is not completed for cert project with id "
            f"{cert_project_id}."
        )
        if ignore_publishing_checklist:
            return
        sys.exit(1)


def main() -> None:
    """
    Main function
    """
    parser = setup_argparser()
    args = parser.parse_args()

    log_level = "INFO"
    if args.verbose:
        log_level = "DEBUG"
    setup_logger(level=log_level)

    check_hydra_checklist_status(
        args.cert_project_id, args.hydra_url, args.ignore_publishing_checklist == "true"
    )


if __name__ == "__main__":  # pragma: no cover
    main()

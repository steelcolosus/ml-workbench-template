import json
import subprocess

import pandas as pd
import pkg_resources

from libs.log.log_config import get_logger

logger = get_logger("diagnostics")


def outdated_packages_list():
    """
    This function checks if there are any outdated packages in the current
    Python environment.

    Returns:
        list: list of dictionaries of outdated packages
    """
    # read requirements.txt and build a data frame with package names and versions
    logger.info("Reading requirements.txt")
    with open("requirements.txt") as f:
        requirements = f.read().splitlines()
    packages = {}
    for r in requirements:
        if "==" in r:
            name, version = r.split("==")
        else:
            name = r
            try:
                version = pkg_resources.get_distribution(name).version
            except pkg_resources.DistributionNotFound:
                version = "not installed"
        packages[name] = version

    # check if there are any outdated packages in the current Python environment
    logger.info("Checking for outdated packages")
    outdated = subprocess.check_output(
        ["pip", "list", "--outdated", "--format", "json"]
    )

    outdated = json.loads(outdated)
    outdated_packages = []
    for package in outdated:
        if package["name"] in packages:
            if package["latest_version"] != packages[package["name"]]:
                outdated_packages.append(
                    {
                        "Package": package["name"],
                        "Current Version": package["version"],
                        "Latest Version": package["latest_version"],
                    }
                )

    return outdated_packages


if __name__ == "__main__":
    logger.info("Getting outdated packages")
    outdated_packages = outdated_packages_list()
    logger.info("Outdated packages list: {}".format(outdated_packages))
    if outdated_packages:
        packages = pd.DataFrame(outdated_packages).set_index("Package").to_string()
        logger.info("Outdated packages: {}".format(packages))
    else:
        logger.info("No outdated packages found.")

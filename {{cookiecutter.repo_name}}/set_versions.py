import pkg_resources


def update_requirements_file():
    """
    This function updates the requirements.txt file with the installed versions
    of the packages.
    """
    # Read the current requirements.txt file
    with open("requirements.txt") as f:
        requirements = f.read().splitlines()

    updated_requirements = []
    for r in requirements:
        if "==" in r:
            name, version = r.split("==")
        else:
            name = r
            try:
                version = pkg_resources.get_distribution(name).version
            except pkg_resources.DistributionNotFound:
                version = "not installed"

        if version != "not installed":
            updated_requirements.append(f"{name}=={version}")
        else:
            updated_requirements.append(name)

    # Write the updated requirements to the requirements.txt file
    with open("requirements.txt", "w") as f:
        f.write("\n".join(updated_requirements))


if __name__ == "__main__":
    update_requirements_file()
    print("requirements.txt has been updated with installed package versions.")

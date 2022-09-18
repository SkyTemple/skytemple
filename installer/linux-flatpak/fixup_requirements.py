"""This simple script takes in a requirement file and removes "all" packages which are already part of the Sdk."""
import sys, pathlib, pkg_resources

# this is an incomplete list!
SYSTEM_PACKAGES = ["pycairo"]
PATH = sys.argv[1]

with pathlib.Path(PATH).open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement
        in pkg_resources.parse_requirements(requirements_txt)
    ]
    for requirement in install_requires:
        # This is a bit naive but it's good enough:
        if not any(requirement.startswith(x) for x in SYSTEM_PACKAGES):
            print(requirement)

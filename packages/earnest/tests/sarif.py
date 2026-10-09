"""SARIF helpers the tests share: the one run in a log, and where a result sits."""

import json


def sarif_run(text):
    """Return the one run of the SARIF log in text."""
    (run,) = json.loads(text)["runs"]
    return run


def located(result):
    """Return a result's file, as its percent-encoded uri, and its line."""
    location = result["locations"][0]["physicalLocation"]
    return location["artifactLocation"]["uri"], location["region"]["startLine"]

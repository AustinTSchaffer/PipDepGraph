#!/usr/bin/env python

import asyncio
import argparse
import json
from typing import Optional
import logging
import sys

import aiohttp
import requests
import jsonpath_ng
PYPI_ENDPOINT = "https://pypi.org/pypi"

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

async def get_package_info_async(session: aiohttp.ClientSession, package: str, version: Optional[str]=None) -> dict:
    """
    """

    uri = (
        f'{PYPI_ENDPOINT}/{package}/{version}/json'
        if version else
        f'{PYPI_ENDPOINT}/{package}/json'
    )

    async with session.get(uri) as response:
        return await response.json()


def get_package_info(package: str, version: Optional[str]=None, jsonpath: Optional[str]=None) -> dict:
    """
    """

    resp = (
        requests.get(f'{PYPI_ENDPOINT}/{package}/{version}/json')
        if version else
        requests.get(f'{PYPI_ENDPOINT}/{package}/json')
    )

    if resp.ok:
        if jsonpath:
            results = [
                match.value
                for match in
                jsonpath_ng.parse(jsonpath).find(resp.json())
            ]
            if not results:
                return None
            elif len(results) > 1:
                return results
            else:
                return results[0]

        return resp.json()

    raise ValueError(f"Error from PyPI. Status code: {resp.status_code}")

def main():
    parser = argparse.ArgumentParser(description="Pulls information about packages from PyPI via the /pypi/{package}/json endpoint")
    parser.add_argument(type=str, help="The name of a python package.", dest="package")
    parser.add_argument("--version", "-v", type=str, help="The optional version of a python package.", dest="version")
    parser.add_argument("--json-path", "--jp", "-p", type=str, help="A JSONPath expression for limiting the output.", dest="jsonpath")

    args = parser.parse_args()
    try:
        info = get_package_info(args.package, args.version, args.jsonpath)
    except Exception as e:
        print(e)
        exit(1)

    print(json.dumps(info))

if __name__ == "__main__":
    main()

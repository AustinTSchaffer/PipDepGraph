#%% Get List of Packages

import requests
import bs4

print("Loading package names...")

simple_index_resp = requests.get("https://pypi.org/simple")
soup = bs4.BeautifulSoup(simple_index_resp.text, "html.parser")
package_names = ( link.text for link in soup.find_all('a') )

# %% Get Versions for Each Package

import asyncio
import dataclasses
from typing import Optional, Iterator

import aiohttp
from aiostream import stream, pipe, async_
import aiocouch

import pydeps

@dataclasses.dataclass
class PackageInfo:
    name: str
    info: dict

async def get_package_info(session: aiohttp.ClientSession, package_name: str) -> tuple[Optional[Exception], PackageInfo]:
    try:
        package_info = await pydeps.get_package_info_async(
            session=session,
            package=package_name,
        )
        return None, PackageInfo(package_name, package_info)
    except Exception as e:
        return e, PackageInfo(package_name, {})

async def db_doesnt_contain_record(db: aiocouch.database.Database, package_name: str) -> bool:
    doc = aiocouch.document.Document(db, package_name)
    return not await doc._exists()

async def insert_record(db: aiocouch.database.Database, record: PackageInfo):
    doc = await db.create(
        id=record.name,
        exists_ok=True,
        data=record.info,
    )

    await doc.save()

async def main():
    async with aiohttp.ClientSession() as session:
        async with aiocouch.CouchDB("http://localhost:5984", user="pydeps", password="pydeps") as couchdb:
            db = await couchdb.create("db", exists_ok=True)

            await (
                stream.iterate(package_names)
                | pipe.filter(async_(lambda name: db_doesnt_contain_record(db, name)))
                | pipe.map(async_(lambda name: get_package_info(session, name)))
                | pipe.filter(lambda result: not result[0])
                | pipe.map(lambda result: result[1])
                | pipe.action(async_(lambda record: insert_record(db, record)))
            )

print("Fetching package info...")
asyncio.run(main())

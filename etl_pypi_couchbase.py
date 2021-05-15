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
import aiostream
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

async def db_contains_record(db: aiocouch.database.Database, package_name: str) -> bool:
    doc = aiocouch.document.Document(db, package_name)
    return await doc._exists()

async def insert_record(db: aiocouch.database.Database, record: PackageInfo):
    doc = await db.create(
        id=record.name,
        data=record.info,
    )

    await doc.save()

async def main():
    async with aiohttp.ClientSession() as session:
        async with aiocouch.CouchDB("http://localhost:5984", user="pydeps", password="pydeps") as couchdb:
            db = await couchdb.create("db", exists_ok=True)

            package_name_stream = aiostream.stream.iterate(package_names)
            async with package_name_stream.stream() as streamer:
                async for package_name in streamer:
                    if await db_contains_record(db, package_name):
                        print(f"DB already contains package: {package_name}")
                        continue

                    error, package_info = await get_package_info(session, package_name)

                    if error:
                        print(f"Cant save package: {package_name}. Reason:", error)
                        continue

                    print(f"Inserting package into CouchDB: {package_name}")
                    await insert_record(db, package_info)

print("Fetching package info...")
asyncio.run(main())

import asyncio
import json

from database import init_db, init_teams

OUTPUT_FILE = "teams.json"


async def main():
    await init_db()
    await init_teams()

    from database import teams

    assert teams is not None
    data = await teams.find({}).to_list(length=None)

    for doc in data:
        doc["_id"] = str(doc["_id"])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Dumped {len(data)} documents to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())

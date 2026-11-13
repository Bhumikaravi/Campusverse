import asyncio
from datetime import datetime
import app.database as d
import app.middleware.auth as a

async def main():
    await d.connect_db()
    db = d.get_db()
    pwd = a.hash_password("Admin@123")
    now = datetime.now()
    res = await db["users"].update_one(
        {"email": "admin@campusverse.edu"},
        {"$set": {
            "email": "admin@campusverse.edu",
            "full_name": "CampusVerse Admin",
            "name": "CampusVerse Admin",
            "role": "admin",
            "department": "Administration",
            "hashed_password": pwd,
            "passwordHash": pwd,
            "created_at": now,
            "updated_at": now,
            "createdAt": now
        }},
        upsert=True
    )
    print("SUCCESS: Admin user 'admin@campusverse.edu' seeded with role 'admin'!")
    await d.close_db()

if __name__ == "__main__":
    asyncio.run(main())

import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

async def set_role(email: str, role: str):
    if role not in ["student", "moderator", "admin"]:
        print(f"Error: Invalid role '{role}'. Must be one of: student, moderator, admin")
        sys.exit(1)

    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]
    
    result = await db["users"].find_one_and_update(
        {"email": email.lower().strip()},
        {"$set": {"role": role}},
        return_document=True
    )

    if not result:
        print(f"User with email '{email}' not found.")
        sys.exit(1)

    print(f"Success! Updated user '{result.get('name')}' ({email}) to role '{role}'.")
    client.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m app.scripts.set_role <email> <role>")
        print("Example: python -m app.scripts.set_role admin@campusverse.edu admin")
        sys.exit(1)

    email_arg = sys.argv[1]
    role_arg = sys.argv[2]
    asyncio.run(set_role(email_arg, role_arg))

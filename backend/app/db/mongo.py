import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING

log = logging.getLogger("app.db.mongo")


class MongoDBManager:
    """Async MongoDB Connection Manager using Motor."""

    def __init__(self):
        self.client: AsyncIOMotorClient | None = None
        self.db: AsyncIOMotorDatabase | None = None

    async def connect(self, uri: str, db_name: str):
        """Initialize Motor client and connect to database."""
        log.info("Connecting to MongoDB at %s (db: %s)", uri, db_name)
        self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        await self.setup_indexes()
        log.info("MongoDB connection and index setup completed successfully")

    async def close(self):
        """Close Motor client connection."""
        if self.client:
            log.info("Closing MongoDB connection")
            self.client.close()
            self.client = None
            self.db = None

    async def setup_indexes(self):
        """Set up indexes for query_logs and collections."""
        if self.db is None:
            return

        query_logs = self.db["query_logs"]

        indexes = [
            # Unique request_id index
            IndexModel([("request_id", ASCENDING)], unique=True, name="idx_unique_request_id"),
            # Compound user history index sorted by date
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="idx_user_created"),
            # General date index for analytics
            IndexModel([("created_at", DESCENDING)], name="idx_created_at"),
            # Model performance index
            IndexModel([("final_model", ASCENDING)], name="idx_final_model"),
            # Quality pass status index
            IndexModel([("passed", ASCENDING)], name="idx_passed"),
        ]

        try:
            await query_logs.create_indexes(indexes)
            log.info("Collection 'query_logs' indexes created successfully")
        except Exception as exc:
            log.warning("Index creation warning (MongoDB server may be offline/standalone): %s", exc)

    def get_collection(self, name: str = "query_logs") -> AsyncIOMotorCollection:
        """Get collection handle."""
        if self.db is None:
            raise RuntimeError("Database connection is not initialized. Call connect() first.")
        return self.db[name]


db_manager = MongoDBManager()


def get_query_logs() -> AsyncIOMotorCollection:
    """Dependency helper to get query_logs collection."""
    return db_manager.get_collection("query_logs")

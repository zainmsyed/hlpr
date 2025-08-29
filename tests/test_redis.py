#!/usr/bin/env python3
"""Test script for Redis integration."""
import asyncio
import sys
import logging
from pathlib import Path

# Configure logging to see error messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from hlpr.core.redis_client import test_redis_connection, redis_set, redis_get, redis_delete


async def test_redis_operations():
    """Test basic Redis operations."""
    print("🧪 Testing Redis Integration...")

    # Test connection
    print("1. Testing connection...")
    try:
        connected = await test_redis_connection()
        if not connected:
            print("❌ Redis connection failed!")
            return False
        print("✅ Redis connection successful!")
    except Exception as e:
        print(f"❌ Redis connection error: {e}")
        return False

    # Test basic operations
    print("2. Testing basic operations...")

    # Set a value
    key = "test:key"
    value = "Hello, Redis!"
    success = await redis_set(key, value, ttl=60)  # 60 second TTL
    if not success:
        print("❌ Failed to set value!")
        return False
    print(f"✅ Set key '{key}' to '{value}'")

    # Get the value
    retrieved = await redis_get(key)
    if retrieved != value:
        print(f"❌ Retrieved value mismatch! Expected: {value}, Got: {retrieved}")
        return False
    print(f"✅ Retrieved value: '{retrieved}'")

    # Delete the key
    deleted = await redis_delete(key)
    if deleted != 1:
        print("❌ Failed to delete key!")
        return False
    print("✅ Deleted key successfully")

    # Verify deletion
    exists_after = await redis_get(key)
    if exists_after is not None:
        print("❌ Key still exists after deletion!")
        return False
    print("✅ Key properly deleted")

    print("🎉 All Redis tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_redis_operations())
    sys.exit(0 if success else 1)
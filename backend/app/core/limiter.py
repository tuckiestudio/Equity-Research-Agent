"""
Rate limiter configuration using slowapi.
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Disable rate limiting in test environment
if os.getenv("TESTING", "false").lower() == "true":
    # In test mode, use a no-op limiter
    limiter = Limiter(key_func=get_remote_address, enabled=False)
else:
    # Initialize rate limiter with IP-based key function
    limiter = Limiter(key_func=get_remote_address)

"""
Rate limiter configuration using slowapi.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter with IP-based key function
limiter = Limiter(key_func=get_remote_address)

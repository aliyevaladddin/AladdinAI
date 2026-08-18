# NOTICE: This file is protected under RCF-PL
"""Shared rate limiter — import from here to avoid circular imports."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

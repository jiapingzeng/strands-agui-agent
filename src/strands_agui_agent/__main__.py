"""
Main entry point for running the Strands AG-UI Agent server.
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
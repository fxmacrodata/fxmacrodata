# Synchronous
from fxmacrodata import Client

client = Client(api_key="YOUR_API_KEY")
data = client.get("aud", "policy_rate", start_date="2023-01-01", end_date="2023-11-01")
print(data)

# Async
import asyncio
from fxmacrodata import AsyncClient

async def main():
    async with AsyncClient(api_key="YOUR_RAPIDAPI_KEY") as client:
        data = await client.get("eur", "cpi")
        print(data)

asyncio.run(main())

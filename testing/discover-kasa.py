import asyncio
from kasa import Discover

async def discover():
  discovered = await Discover.discover()
  for ip, device in discovered.items():
      await device.update()
      print(f'{ip}: {device.alias}')

asyncio.run(discover())

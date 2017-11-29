class Class1(object):
    async def get(self):
        return await asyncio.sleep(0)


if __name__ == '__main__':
    import asyncio

from aiolimiter import AsyncLimiter
import asyncio

class ThrottledLLM:
    def __init__(self,llm,max_calls_per_minute=60):
        self.llm=llm
        self.limiter = AsyncLimiter(max_calls_per_minute, time_period=60)
    
    async def invoke(self, prompt):
        async with self.limiter:
            return await asyncio.to_thread(self.llm.invoke,prompt)
        
    def __getattr__(self,attr):
        print(self.llm,"-----------------------------llm--------------------------------")
        return getattr(self.llm,attr)
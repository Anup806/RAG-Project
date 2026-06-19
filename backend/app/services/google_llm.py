import asyncio
import logging
import threading
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

from app.core.config import settings
from app.rag.prompt import SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)


class GoogleLLMClient:
    def __init__(self) -> None:
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY is not set; generation calls will fail until configured.")
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY or None)
        self.model = settings.GOOGLE_LLM_MODEL

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[str | Exception | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def worker() -> None:
            try:
                response = self._client.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=settings.GOOGLE_TEMPERATURE,
                        max_output_tokens=settings.GOOGLE_MAX_OUTPUT_TOKENS,
                    ),
                )
                for chunk in response:
                    text = getattr(chunk, "text", None)
                    if text:
                        asyncio.run_coroutine_threadsafe(queue.put(text), loop)
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(queue.put(exc), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    async def complete(self, prompt: str) -> str:
        chunks: list[str] = []
        async for token in self.stream(prompt):
            chunks.append(token)
        return "".join(chunks)


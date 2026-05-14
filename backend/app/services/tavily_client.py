from langchain_tavily import TavilySearch

MAX_RAG_CONTENT_CHARS = 3000
MAX_SNIPPET_CHARS = 500
DEFAULT_MAX_RESULTS = 5


class TavilyService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.tool = TavilySearch(
            max_results=DEFAULT_MAX_RESULTS,
            topic="general",
            search_depth="basic",
            include_answer="basic",
            include_raw_content=True,
            tavily_api_key=api_key,
        )

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        import asyncio
        import json

        tool = self.tool
        if max_results != DEFAULT_MAX_RESULTS:
            tool = TavilySearch(
                max_results=max_results,
                topic="general",
                search_depth="basic",
                include_answer="basic",
                include_raw_content=True,
                tavily_api_key=self.api_key,
            )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: tool.invoke({"query": query}),
        )

        # TavilySearch returns a JSON string
        if isinstance(result, str):
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                return []
        else:
            data = result
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"Tavily search failed: {data['error']}")

        sources = []
        seen_urls: set[str] = set()
        for r in (data.get("results") if isinstance(data, dict) else data) or []:
            url = r.get("url", "")
            if url and url in seen_urls:
                continue
            seen_urls.add(url)

            content = (
                r.get("raw_content")
                or r.get("content")
                or r.get("snippet")
                or ""
            ).strip()
            sources.append({
                "title": r.get("title", ""),
                "url": url,
                "snippet": content[:MAX_SNIPPET_CHARS],
                "content": content[:MAX_RAG_CONTENT_CHARS],
                "score": r.get("score", 0),
            })

        return sources

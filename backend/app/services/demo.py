import asyncio
from collections.abc import AsyncIterator


DEMO_SOURCES = {
    "rag": [
        {
            "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
            "url": "https://arxiv.org/abs/2005.11401",
            "snippet": "RAG combines a retriever with a generator so answers can be grounded in retrieved documents.",
            "content": (
                "Retrieval-Augmented Generation combines parametric generation with non-parametric "
                "retrieval. The retriever supplies relevant passages, and the generator uses them as "
                "grounding context for knowledge-intensive tasks."
            ),
            "score": 0.94,
        },
        {
            "title": "LangChain RAG concepts",
            "url": "https://python.langchain.com/docs/concepts/rag/",
            "snippet": "RAG applications retrieve external context before asking a language model to answer.",
            "content": (
                "A RAG application retrieves relevant information from external sources, inserts it "
                "into the model prompt, and asks the model to answer using that context."
            ),
            "score": 0.88,
        },
    ],
    "react server components": [
        {
            "title": "React Server Components",
            "url": "https://react.dev/reference/rsc/server-components",
            "snippet": "Server Components run on the server and can read server-side data sources directly.",
            "content": (
                "React Server Components are rendered before bundling and can run on the server. "
                "They can access server-side data sources and reduce client-side JavaScript."
            ),
            "score": 0.93,
        },
        {
            "title": "Next.js Server and Client Components",
            "url": "https://nextjs.org/docs/app/getting-started/server-and-client-components",
            "snippet": "Next.js uses Server Components by default in the App Router.",
            "content": (
                "In the Next.js App Router, components are Server Components by default. Client "
                "Components are used when interactivity, browser APIs, or client state are needed."
            ),
            "score": 0.87,
        },
    ],
    "quantum": [
        {
            "title": "IBM Quantum Computing",
            "url": "https://www.ibm.com/quantum",
            "snippet": "Quantum computing uses quantum mechanics to process information in new ways.",
            "content": (
                "Quantum computing uses principles such as superposition and entanglement. Qubits "
                "can represent richer state than classical bits, which may help with some simulation "
                "and optimization problems."
            ),
            "score": 0.9,
        },
        {
            "title": "Microsoft Azure Quantum overview",
            "url": "https://azure.microsoft.com/products/quantum",
            "snippet": "Quantum systems are explored for chemistry, optimization, and materials problems.",
            "content": (
                "Quantum computing is being explored for chemistry simulation, optimization, and "
                "materials science. Current hardware is still developing, so practical applications "
                "often combine classical and quantum workflows."
            ),
            "score": 0.84,
        },
    ],
}


DEFAULT_DEMO_SOURCES = [
    {
        "title": "Me1ody AI Search demo source",
        "url": "https://example.com/me1ody-demo",
        "snippet": "Demo mode uses local prepared sources so the full search pipeline can be shown offline.",
        "content": (
            "Demo mode returns prepared local sources, runs the same cleaning, RAG, citation audit, "
            "history saving, and frontend streaming flow, and avoids consuming external API quota."
        ),
        "score": 0.8,
    }
]


def pick_demo_sources(query: str) -> list[dict]:
    normalized = query.lower()
    if "react server components" in normalized or "server component" in normalized:
        return DEMO_SOURCES["react server components"]
    if "量子" in query or "quantum" in normalized:
        return DEMO_SOURCES["quantum"]
    if "rag" in normalized or "检索增强" in query:
        return DEMO_SOURCES["rag"]
    return DEFAULT_DEMO_SOURCES


class DemoTavilyService:
    async def search(self, query: str) -> list[dict]:
        await asyncio.sleep(0.05)
        return pick_demo_sources(query)


class DemoDeepseekService:
    async def stream_answer(
        self,
        query: str,
        sources: list[dict],
        conversation_history: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        topic = query.strip() or "这个问题"
        source_count = len(sources)
        answer = (
            f"这是 Demo 模式下对“{topic}”的稳定演示回答。\n\n"
            f"系统先召回并清洗了 {source_count} 个来源，再通过本地向量检索选出最相关片段，"
            "最后基于这些片段生成答案。核心设计是让模型回答必须落在可追溯来源上，"
            "因此页面会展示来源列表、检索链路和引用审计结果。[1]\n\n"
            "在复试现场，这个模式可以避免网络波动、第三方 API 限额或模型响应慢导致演示中断；"
            "正式模式仍会调用 Tavily 和 DeepSeek 完成真实搜索。"
        )
        if len(sources) > 1:
            answer += " 第二个来源可用于交叉验证主要结论。[2]"

        for token in answer.split(" "):
            await asyncio.sleep(0.01)
            yield token + " "

    async def suggest_followups(self, query: str, answer: str) -> list[str]:
        return [
            "这个项目的 RAG 流程如何设计？",
            "如何保证回答不会脱离来源？",
            "Demo 模式和正式搜索模式有什么区别？",
        ]

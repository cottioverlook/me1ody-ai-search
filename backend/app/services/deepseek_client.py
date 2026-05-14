from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek

from app.utils.prompts import build_followup_prompt, build_system_prompt, build_user_prompt, detect_query_intent


class DeepseekService:
    def __init__(self, api_key: str):
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            temperature=0.3,
            max_tokens=4096,
            api_key=api_key,
        )

    async def stream_answer(
        self,
        query: str,
        sources: list[dict],
        conversation_history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        intent = detect_query_intent(query)
        system_prompt = build_system_prompt(intent)
        user_prompt = build_user_prompt(query, sources, intent)

        messages = [SystemMessage(content=system_prompt)]
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    from langchain_core.messages import AIMessage
                    messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=user_prompt))

        async for chunk in self.llm.astream(messages):
            if chunk.content:
                yield chunk.content

    async def suggest_followups(self, query: str, answer: str) -> list[str]:
        prompt = build_followup_prompt(query, answer)
        response = await self.llm.ainvoke(
            [HumanMessage(content=prompt)],
            config={"configurable": {"max_tokens": 200}},
        )
        text = response.content or ""
        questions = [q.strip() for q in text.strip().split("\n") if q.strip()]
        return questions[:5]

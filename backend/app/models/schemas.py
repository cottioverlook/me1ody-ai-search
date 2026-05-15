from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    conversation_id: str | None = None


class Source(BaseModel):
    title: str
    url: str
    snippet: str
    score: float | None = None
    source_score: float | None = None
    quality_score: float | None = None
    quality_label: str | None = None
    source_type: str | None = None
    source_type_label: str | None = None
    citation_index: int | None = None


class HistoryMessage(BaseModel):
    role: str
    content: str
    sources: list[Source] | None = None


class ConversationResponse(BaseModel):
    id: str
    share_id: str
    title: str
    created_at: str
    is_favorite: bool
    messages: list[HistoryMessage]


class ConversationListItem(BaseModel):
    id: str
    share_id: str
    title: str
    created_at: str
    is_favorite: bool


class FavoriteRequest(BaseModel):
    is_favorite: bool

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages


class Article(TypedDict):
    id: str
    title: str
    url: str
    source: str
    published_date: str
    content: str
    relevance_score: float
    credibility_score: float
    deal_type: str
    companies: List[str]
    deal_value: str
    geography: str


class NewsletterState(TypedDict):
    messages: Annotated[list, add_messages]
    market: str
    as_of_date: str
    raw_articles: List[Article]
    deduplicated_articles: List[Article]
    filtered_articles: List[Article]
    credibility_checked_articles: List[Article]
    newsletter_draft: str
    newsletter_sections: dict
    csv_data: str
    run_id: str
    status: str
    error: Optional[str]

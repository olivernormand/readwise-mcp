"""Readwise MCP Server - provides read/write access to Readwise highlights."""

import os
from datetime import datetime
from typing import Literal

import httpx
from fastmcp import FastMCP

from readwise_mcp.models import (
    CreateHighlightRequest,
    CreateHighlightsBatchRequest,
    ExportParams,
    GetHighlightsParams,
    ListBooksParams,
)

BASE_URL = os.environ.get("BASE_URL", "https://readwise.io")
mcp = FastMCP("Readwise MCP")

FullTextQueryField = Literal[
    "document_author",
    "document_title",
    "highlight_note",
    "highlight_plaintext",
    "highlight_tags",
]


def get_token() -> str:
    """Get the Readwise API token from environment."""
    token = os.environ.get("ACCESS_TOKEN")
    if not token:
        raise ValueError("ACCESS_TOKEN environment variable not set")
    return token


def get_mcp_headers() -> dict[str, str]:
    """Get headers for MCP API requests."""
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Access-Token": get_token(),
    }


def get_api_headers() -> dict[str, str]:
    """Get headers for standard v2 API requests."""
    return {"Authorization": f"Token {get_token()}"}


async def initialize_mcp() -> None:
    """Call the MCP initialization endpoint."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{BASE_URL}/api/mcp/initialize",
                headers=get_mcp_headers(),
            )
        except Exception as e:
            print(f"Failed to call MCP initialization endpoint: {e}")


# === MCP Endpoints ===


@mcp.tool()
async def search_highlights(
    vector_search_term: str,
    full_text_queries: list[dict] | None = None,
) -> list[dict]:
    """Search Readwise highlights using semantic/vector search.

    Use this to find highlights by meaning, not just exact text matches. Great for
    finding quotes about a topic, discovering connections between ideas, or locating
    half-remembered passages.

    Args:
        vector_search_term: The semantic search query (e.g., "productivity habits",
            "stoic philosophy", "machine learning basics")
        full_text_queries: Optional filters to narrow results (max 8). Each filter has:
            - field_name: One of "document_author", "document_title",
              "highlight_note", "highlight_plaintext", "highlight_tags"
            - search_term: Text to match in that field
            Example: [{"field_name": "document_author", "search_term": "Cal Newport"}]

    Returns:
        List of highlights, each containing:
        - id: Highlight ID
        - score: Relevance score
        - attributes: Object with document_title, document_author, highlight_plaintext,
          highlight_note, highlight_tags, document_category, document_tags

    Example use cases:
        - "Find highlights about deep work" -> vector_search_term="deep work practices"
        - "What did Marcus Aurelius say about death?" -> vector_search_term="death mortality"
          with full_text_queries=[{"field_name": "document_author", "search_term": "Aurelius"}]
    """
    payload: dict = {"vector_search_term": vector_search_term}
    if full_text_queries:
        payload["full_text_queries"] = full_text_queries[:8]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/mcp/highlights",
            headers=get_mcp_headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json().get("results", [])


# === V2 API Endpoints ===


@mcp.tool()
async def verify_token() -> dict:
    """Verify that the Readwise API token is valid.

    Use this to check if the configured ACCESS_TOKEN is valid before making other
    API calls. Useful for debugging connection issues.

    Returns:
        {"valid": True, "message": "Token is valid"} if the token is valid.
        Raises an error if the token is invalid or missing.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v2/auth/",
            headers=get_api_headers(),
        )
        if response.status_code == 204:
            return {"valid": True, "message": "Token is valid"}
        response.raise_for_status()
        return {"valid": False, "message": "Unexpected response"}


@mcp.tool()
async def list_books(
    category: Literal["books", "articles", "tweets", "supplementals", "podcasts"] | None = None,
    source: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    updated_gt: str | None = None,
    updated_lt: str | None = None,
    last_highlight_at_gt: str | None = None,
    last_highlight_at_lt: str | None = None,
) -> dict:
    """List books and documents in your Readwise library.

    Use this to browse your library, find book IDs for other operations, or see what
    you've been reading recently. Supports filtering by category and date ranges.

    Args:
        category: Filter by type - "books", "articles", "tweets", "supplementals", "podcasts"
        source: Filter by source (e.g., "kindle", "instapaper", "pocket")
        page: Page number for pagination (starts at 1)
        page_size: Results per page (default 100, max 1000)
        updated_gt: Only books updated after this ISO datetime (e.g., "2024-01-01T00:00:00Z")
        updated_lt: Only books updated before this ISO datetime
        last_highlight_at_gt: Only books with highlights made after this datetime
        last_highlight_at_lt: Only books with highlights made before this datetime

    Returns:
        Paginated response containing:
        - count: Total number of books matching filters
        - next: URL for next page (null if no more pages)
        - previous: URL for previous page
        - results: List of books, each with:
            - id: Book ID (use this with get_book_highlights)
            - title: Book title
            - author: Author name
            - category: Type of document
            - source: Where it was imported from
            - num_highlights: Number of highlights in this book
            - last_highlight_at: When the last highlight was made
            - cover_image_url: Cover image URL

    Example use cases:
        - "What books have I highlighted?" -> list_books(category="books")
        - "Recent articles" -> list_books(category="articles", last_highlight_at_gt="2024-01-01")
    """
    params = ListBooksParams(
        category=category,
        source=source,
        page=page,
        page_size=page_size,
        updated_gt=datetime.fromisoformat(updated_gt) if updated_gt else None,
        updated_lt=datetime.fromisoformat(updated_lt) if updated_lt else None,
        last_highlight_at_gt=datetime.fromisoformat(last_highlight_at_gt) if last_highlight_at_gt else None,
        last_highlight_at_lt=datetime.fromisoformat(last_highlight_at_lt) if last_highlight_at_lt else None,
    )

    query_params = {}
    if params.category:
        query_params["category"] = params.category
    if params.source:
        query_params["source"] = params.source
    if params.page:
        query_params["page"] = params.page
    if params.page_size:
        query_params["page_size"] = params.page_size
    if params.updated_gt:
        query_params["updated__gt"] = params.updated_gt.isoformat()
    if params.updated_lt:
        query_params["updated__lt"] = params.updated_lt.isoformat()
    if params.last_highlight_at_gt:
        query_params["last_highlight_at__gt"] = params.last_highlight_at_gt.isoformat()
    if params.last_highlight_at_lt:
        query_params["last_highlight_at__lt"] = params.last_highlight_at_lt.isoformat()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v2/books/",
            headers=get_api_headers(),
            params=query_params if query_params else None,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_book_highlights(
    book_id: int,
    page: int | None = None,
    page_size: int | None = None,
    updated_gt: str | None = None,
    updated_lt: str | None = None,
    highlighted_at_gt: str | None = None,
    highlighted_at_lt: str | None = None,
) -> dict:
    """Get all highlights from a specific book.

    Use this when you want to see all highlights from a particular book. First use
    list_books to find the book_id, then use this to retrieve its highlights.

    Args:
        book_id: The ID of the book (get this from list_books)
        page: Page number for pagination (starts at 1)
        page_size: Results per page (default 100, max 1000)
        updated_gt: Only highlights updated after this ISO datetime
        updated_lt: Only highlights updated before this ISO datetime
        highlighted_at_gt: Only highlights made after this ISO datetime
        highlighted_at_lt: Only highlights made before this ISO datetime

    Returns:
        Paginated response containing:
        - count: Total number of highlights
        - next: URL for next page (null if no more)
        - previous: URL for previous page
        - results: List of highlights, each with:
            - id: Highlight ID
            - text: The highlighted text
            - note: Your note on the highlight (if any)
            - location: Position in the book (page number, etc.)
            - location_type: Type of location ("page", "order", "time_offset")
            - color: Highlight color
            - highlighted_at: When the highlight was made
            - url: Link to the highlight
            - tags: List of tags applied to this highlight

    Example use cases:
        - "Show me highlights from Atomic Habits" -> First list_books to find ID,
          then get_book_highlights(book_id=12345)
        - "Recent highlights from this book" -> get_book_highlights(book_id=123,
          highlighted_at_gt="2024-06-01")
    """
    params = GetHighlightsParams(
        book_id=book_id,
        page=page,
        page_size=page_size,
        updated_gt=datetime.fromisoformat(updated_gt) if updated_gt else None,
        updated_lt=datetime.fromisoformat(updated_lt) if updated_lt else None,
        highlighted_at_gt=datetime.fromisoformat(highlighted_at_gt) if highlighted_at_gt else None,
        highlighted_at_lt=datetime.fromisoformat(highlighted_at_lt) if highlighted_at_lt else None,
    )

    query_params = {"book_id": params.book_id}
    if params.page:
        query_params["page"] = params.page
    if params.page_size:
        query_params["page_size"] = params.page_size
    if params.updated_gt:
        query_params["updated__gt"] = params.updated_gt.isoformat()
    if params.updated_lt:
        query_params["updated__lt"] = params.updated_lt.isoformat()
    if params.highlighted_at_gt:
        query_params["highlighted_at__gt"] = params.highlighted_at_gt.isoformat()
    if params.highlighted_at_lt:
        query_params["highlighted_at__lt"] = params.highlighted_at_lt.isoformat()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v2/highlights/",
            headers=get_api_headers(),
            params=query_params,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_daily_review() -> dict:
    """Get today's Daily Review highlights for spaced repetition.

    Readwise's Daily Review resurfaces your highlights using spaced repetition to
    help you remember what you've read. Use this to fetch today's review batch.

    Returns:
        Response containing:
        - review_id: Unique ID for this review session
        - review_url: URL to complete the review in Readwise web app
        - review_completed: Whether today's review has been completed
        - highlights: List of highlights to review, each with:
            - id: Highlight ID
            - text: The highlighted text
            - note: Your note (if any)
            - title: Source document title
            - author: Source document author
            - url: Link to the highlight
            - source_url: Link to the original source
            - source_type: Type of source
            - category: Document category
            - highlighted_at: When it was highlighted
            - image_url: Cover image (if available)

    Example use cases:
        - "What should I review today?" -> get_daily_review()
        - "Show me my spaced repetition highlights" -> get_daily_review()
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v2/review/",
            headers=get_api_headers(),
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def export_highlights(
    updated_after: str | None = None,
    book_ids: list[int] | None = None,
    page_cursor: str | None = None,
) -> dict:
    """Bulk export all highlights, optionally filtered by date or book.

    Use this for large exports or syncing. Returns books with their highlights nested
    inside, which is more efficient than fetching each book separately. Supports
    cursor-based pagination for large libraries.

    Args:
        updated_after: Only highlights updated after this ISO datetime
            (e.g., "2024-01-01T00:00:00Z"). Useful for incremental syncs.
        book_ids: Only export from these specific book IDs
        page_cursor: Pagination cursor from a previous response's nextPageCursor

    Returns:
        Response containing:
        - count: Total number of books in export
        - nextPageCursor: Cursor for next page (null if no more pages)
        - results: List of books, each containing:
            - user_book_id: Book ID
            - title: Book title
            - author: Author name
            - readable_title: Formatted title
            - source: Import source
            - cover_image_url: Cover image
            - unique_url: Readwise URL for this book
            - category: Document type
            - readwise_url: Link to book in Readwise
            - source_url: Original source URL
            - tags: Book-level tags
            - highlights: List of highlights with id, text, note, location, color,
              highlighted_at, created_at, updated, tags, etc.

    Example use cases:
        - "Export all my highlights" -> export_highlights()
        - "What did I highlight this month?" -> export_highlights(updated_after="2024-06-01")
        - "Export just these books" -> export_highlights(book_ids=[123, 456])
    """
    params = ExportParams(
        updated_after=datetime.fromisoformat(updated_after) if updated_after else None,
        book_ids=book_ids,
        page_cursor=page_cursor,
    )

    query_params = {}
    if params.updated_after:
        query_params["updatedAfter"] = params.updated_after.isoformat()
    if params.book_ids:
        query_params["ids"] = ",".join(str(id) for id in params.book_ids)
    if params.page_cursor:
        query_params["pageCursor"] = params.page_cursor

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v2/export/",
            headers=get_api_headers(),
            params=query_params if query_params else None,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def create_highlight(
    text: str,
    title: str,
    author: str | None = None,
    image_url: str | None = None,
    source_url: str | None = None,
    source_type: str | None = None,
    category: Literal["books", "articles", "tweets", "supplementals", "podcasts"] | None = None,
    note: str | None = None,
    location: int | None = None,
    location_type: Literal["page", "order", "time_offset"] | None = None,
    highlighted_at: str | None = None,
    highlight_url: str | None = None,
) -> dict:
    """Create a new highlight in Readwise.

    Use this to save a quote, passage, or any text you want to remember. The highlight
    will be added to your Readwise library and included in Daily Review.

    Highlights are deduplicated by title + author + text + source_url, so creating
    the same highlight twice will update the existing one.

    Args:
        text: The highlight text (required, max 8191 chars)
        title: Title of the source - book name, article title, etc. (required)
        author: Author of the source
        image_url: URL for a cover image
        source_url: URL where the content came from
        source_type: Custom source identifier
        category: Type of content - "books", "articles", "tweets", "supplementals", "podcasts"
        note: Your personal note about this highlight
        location: Position in source (page number, paragraph, timestamp)
        location_type: How to interpret location - "page", "order", or "time_offset"
        highlighted_at: When the highlight was made (ISO datetime, defaults to now)
        highlight_url: Direct URL to this specific highlight

    Returns:
        Book info containing:
        - id: Book ID
        - title: Book title
        - author: Author name
        - category: Document category
        - num_highlights: Total highlights in this book
        - modified_highlights: List of highlight IDs that were created/updated

    Example use cases:
        - Save a quote: create_highlight(text="The quote...", title="Book Name", author="Author")
        - Save from article: create_highlight(text="...", title="Article", source_url="https://...")
        - Add personal note: create_highlight(text="...", title="...", note="Why this matters to me")
    """
    request = CreateHighlightRequest(
        text=text,
        title=title,
        author=author,
        image_url=image_url,
        source_url=source_url,
        source_type=source_type,
        category=category,
        note=note,
        location=location,
        location_type=location_type,
        highlighted_at=datetime.fromisoformat(highlighted_at) if highlighted_at else None,
        highlight_url=highlight_url,
    )

    payload = {"highlights": [request.model_dump(exclude_none=True)]}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v2/highlights/",
            headers=get_api_headers(),
            json=payload,
        )
        response.raise_for_status()
        results = response.json()
        return results[0] if results else {}


@mcp.tool()
async def create_highlights_batch(
    highlights: list[dict],
) -> list[dict]:
    """Create multiple highlights at once.

    Use this when you have several highlights to save - it's more efficient than
    calling create_highlight multiple times. All highlights are processed in a
    single API call.

    Args:
        highlights: List of highlight objects. Each highlight must have:
            - text (required): The highlight text (max 8191 chars)
            - title (required): Title of the source document

            Optional fields per highlight:
            - author: Author of the source
            - image_url: Cover image URL
            - source_url: URL of the source
            - source_type: Custom source identifier
            - category: "books", "articles", "tweets", "supplementals", or "podcasts"
            - note: Your personal note
            - location: Position in source
            - location_type: "page", "order", or "time_offset"
            - highlighted_at: ISO datetime when highlighted
            - highlight_url: Direct URL to highlight

    Returns:
        List of book info objects, each containing:
        - id: Book ID
        - title: Book title
        - author: Author name
        - category: Document category
        - num_highlights: Total highlights in book
        - modified_highlights: List of created/updated highlight IDs

    Example use cases:
        - Import multiple quotes from same book:
          create_highlights_batch(highlights=[
              {"text": "Quote 1...", "title": "Book", "author": "Author"},
              {"text": "Quote 2...", "title": "Book", "author": "Author"},
          ])
        - Batch import from different sources:
          create_highlights_batch(highlights=[
              {"text": "...", "title": "Article 1", "source_url": "https://..."},
              {"text": "...", "title": "Book 1", "author": "Author"},
          ])
    """
    validated_highlights = []
    for h in highlights:
        if "highlighted_at" in h and h["highlighted_at"]:
            h = h.copy()
            h["highlighted_at"] = datetime.fromisoformat(h["highlighted_at"])
        validated_highlights.append(CreateHighlightRequest.model_validate(h))

    request = CreateHighlightsBatchRequest(highlights=validated_highlights)
    payload = {"highlights": [h.model_dump(exclude_none=True) for h in request.highlights]}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v2/highlights/",
            headers=get_api_headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

"""Pydantic models for Readwise API requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# === List Books ===

class ListBooksParams(BaseModel):
    """Parameters for listing books."""

    category: Literal["books", "articles", "tweets", "supplementals", "podcasts"] | None = None
    source: str | None = None
    page: int | None = Field(None, ge=1)
    page_size: int | None = Field(None, ge=1, le=1000)
    updated_gt: datetime | None = None
    updated_lt: datetime | None = None
    last_highlight_at_gt: datetime | None = None
    last_highlight_at_lt: datetime | None = None


# === Get Highlights ===

class GetHighlightsParams(BaseModel):
    """Parameters for getting highlights."""

    book_id: int
    page: int | None = Field(None, ge=1)
    page_size: int | None = Field(None, ge=1, le=1000)
    updated_gt: datetime | None = None
    updated_lt: datetime | None = None
    highlighted_at_gt: datetime | None = None
    highlighted_at_lt: datetime | None = None


# === Export Highlights ===

class ExportParams(BaseModel):
    """Parameters for bulk export."""

    updated_after: datetime | None = None
    book_ids: list[int] | None = None
    page_cursor: str | None = None


# === Recent Highlights ===

class RecentHighlightsParams(BaseModel):
    """Parameters for fetching recent highlights."""

    hours: int = Field(24, ge=1)


# === Create Highlight ===

class CreateHighlightRequest(BaseModel):
    """Request model for creating a single highlight."""

    text: str = Field(..., min_length=1, max_length=8191)
    title: str = Field(..., min_length=1)
    author: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    category: Literal["books", "articles", "tweets", "supplementals", "podcasts"] | None = None
    note: str | None = None
    location: int | None = None
    location_type: Literal["page", "order", "time_offset"] | None = None
    highlighted_at: datetime | None = None
    highlight_url: str | None = None


# === Create Highlights Batch ===

class CreateHighlightsBatchRequest(BaseModel):
    """Request model for creating multiple highlights."""

    highlights: list[CreateHighlightRequest] = Field(..., min_length=1)

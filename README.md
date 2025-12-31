# Readwise MCP Server

An MCP server that provides read/write access to your [Readwise](https://readwise.io) highlights.

## Setup

### 1. Get your Readwise Access Token

1. Go to https://readwise.io/access_token
2. Copy your access token

### 2. Configure Claude Desktop

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "readwise": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/olivernormand/readwise-mcp", "readwise-mcp"],
      "env": {
        "ACCESS_TOKEN": "your_readwise_token_here"
      }
    }
  }
}
```

## Available Tools

### Search & Read

| Tool | Description |
|------|-------------|
| `search_highlights` | Semantic search across all highlights using vector search |
| `list_books` | List books/articles in your library with optional filters |
| `get_book_highlights` | Get all highlights for a specific book |
| `get_daily_review` | Get today's spaced repetition review highlights |
| `export_highlights` | Bulk export highlights with optional date filtering |

### Write

| Tool | Description |
|------|-------------|
| `create_highlight` | Add a single highlight |
| `create_highlights_batch` | Add multiple highlights at once |

### Utility

| Tool | Description |
|------|-------------|
| `verify_token` | Check if your access token is valid |

## Local Development

```bash
# Clone and install
git clone https://github.com/olivernormand/readwise-mcp
cd readwise-mcp
uv sync

# Set your token
export ACCESS_TOKEN="your_token"

# Run the server
uv run readwise-mcp
```

## License

MIT

# MCP

Optional FastMCP adapter over the same core as the CLI.

```bash
pipx install 'walla-cli[mcp]'
walla-mcp          # STDIO
walla-mcp-http     # http://127.0.0.1:8000/mcp/
```

Cursor:

```json
{
  "mcpServers": {
    "walla": {
      "command": "walla-mcp"
    }
  }
}
```

Tools mirror CLI verbs: `instruct`, `search`, `item`, `categories`, `login`,
`inbox`, `thread`, `say`, `offer`, `me`. Envelope matches CLI `--json`.

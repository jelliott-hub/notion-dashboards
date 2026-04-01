#!/bin/bash
# ============================================================
# B4ALL Claude Code MCP Setup Script
# Restores all 6 MCPs for Claude Code terminal use
# Run this in your terminal: bash ~/CommandCenter/setup_claude_mcps.sh
# ============================================================

echo "================================================"
echo "  Setting up Claude Code MCPs (user scope)"
echo "  These will be available across ALL projects"
echo "================================================"
echo ""

# 1. SUPABASE
echo "[1/6] Adding Supabase MCP..."
claude mcp add --transport http supabase --scope user "https://mcp.supabase.com/mcp"
echo "  -> After setup, run /mcp in Claude Code and follow browser login"
echo ""

# 2. NOTION
echo "[2/6] Adding Notion MCP..."
claude mcp add --transport http notion --scope user "https://mcp.notion.com/mcp"
echo "  -> After setup, run /mcp in Claude Code and follow browser login"
echo ""

# 3. HUBSPOT
echo "[3/6] Adding HubSpot MCP..."
claude mcp add --transport http hubspot --scope user "https://mcp.hubspot.com/anthropic"
echo "  -> After setup, run /mcp in Claude Code and follow browser login"
echo ""

# 4. ASANA
echo "[4/6] Adding Asana MCP..."
claude mcp add --transport sse asana --scope user "https://mcp.asana.com/sse"
echo "  -> Note: Asana V1 SSE endpoint sunsets 05/11/2026 - may need to update to HTTP transport"
echo ""

# 5. VERCEL
echo "[5/6] Adding Vercel MCP..."
claude mcp add --transport http vercel --scope user "https://mcp.vercel.com/mcp"
echo "  -> After setup, run /mcp in Claude Code and follow browser login"
echo ""

# 6. FIREFLIES
echo "[6/6] Adding Fireflies MCP..."
claude mcp add --transport http fireflies --scope user "https://api.fireflies.ai/mcp"
echo "  -> After setup, run /mcp in Claude Code and follow browser login"
echo ""

echo "================================================"
echo "  All 6 MCPs added!"
echo ""
echo "  NEXT STEPS:"
echo "  1. Open Claude Code:  claude"
echo "  2. Run:  /mcp"
echo "  3. Authenticate each service in your browser"
echo "  4. Verify with:  claude mcp list"
echo "================================================"

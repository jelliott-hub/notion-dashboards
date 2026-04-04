# Notion CMS in Supabase — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mirror the B4ALL Knowledge Base (715 pages, ~37K blocks, 13 views) into a `notion_cms` Supabase schema so bulk content operations can be staged in SQL and pushed to Notion via API.

**Architecture:** One-time pull from Notion API into Supabase tables (pages, blocks, views, comments, images). SQL-powered editing stages changes into a push queue. A push script processes the queue against the Notion API at 3 req/sec with retry logic. Supabase Storage hosts images with permanent public URLs.

**Tech Stack:** Python 3.14, psycopg2, urllib/requests (Notion API), Supabase Storage REST API. Builds on existing patterns in `scripts/sync_articles_to_db.py`.

**Spec:** `docs/superpowers/specs/2026-04-04-notion-cms-supabase-design.md`

---

## CRITICAL: Target Scope

**There is ONE database. Ignore everything else in the Notion workspace.**

| Field | Value |
|---|---|
| **Database name** | B4ALL Knowledge Base |
| **Database ID** | `37ac70bb-1cc6-4bdc-a52e-f2c8587b636e` |
| **Data Source ID** | `fd44d1a1-ef63-4a64-badb-366b38794cb3` |
| **Database URL** | `https://www.notion.so/37ac70bb1cc64bdca52ef2c8587b636e` |
| **Default view URL** | `https://www.notion.so/37ac70bb1cc64bdca52ef2c8587b636e?v=33713d3677c3814ea37d000c82d297c2` |

This database has ~715 article pages, ~37K content blocks, and 13 views. It lives under the "Company Knowledge Base" page. The workspace has ~90 other data sources — **do NOT query, create, modify, or reference any of them.** Every Notion API call in this plan targets this single database and its pages.

If a Notion MCP tool returns multiple databases, filter to `37ac70bb-1cc6-4bdc-a52e-f2c8587b636e`. If asked to "search" or "list" databases, you already have the ID — don't search.

---

## File Structure

```
projects/notion/
  notion-cms/
    __init__.py
    config.py              -- Env vars, constants, Notion/Supabase config
    notion_client.py       -- Rate-limited Notion API wrapper (reuses sync_articles_to_db.py patterns)
    block_parser.py        -- Parse raw Notion blocks into flat rows with denormalized fields
    media_handler.py       -- Download Notion-hosted media, upload to Supabase Storage
    pull.py                -- One-time pull: Notion → Supabase
    push.py                -- Process push_queue → Notion API
    storage.py             -- Upload branding-assets images to Supabase Storage
    migrate.py             -- Create notion_cms schema + tables
    requirements.txt       -- psycopg2-binary, requests
  tests/
    test_block_parser.py
    test_notion_client.py
    test_media_handler.py
    test_pull.py
    test_push.py
```

---

## Task 1: Schema Migration

**Files:**
- Create: `notion-cms/migrate.py`
- Create: `notion-cms/config.py`
- Create: `notion-cms/__init__.py`
- Create: `notion-cms/requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
# notion-cms/requirements.txt
psycopg2-binary>=2.9
requests>=2.31
```

- [ ] **Step 2: Create config.py**

```python
# notion-cms/config.py
"""Central config — env vars, constants, IDs."""
import os

# Notion
NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_VERSION = "2025-09-03"
NOTION_BASE_URL = "https://api.notion.com/v1"
RATE_LIMIT_DELAY = 0.35  # ~3 req/s

# KB Database
DATABASE_ID = "37ac70bb-1cc6-4bdc-a52e-f2c8587b636e"
DATA_SOURCE_ID = "fd44d1a1-ef63-4a64-badb-366b38794cb3"

# Supabase
SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]  # postgresql://postgres:PASSWORD@db.dozjdswqnzqwvieqvwpe.supabase.co:5432/postgres
SUPABASE_PROJECT_URL = "https://dozjdswqnzqwvieqvwpe.supabase.co"
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]  # for Storage uploads

# Storage
STORAGE_BUCKET = "kb-images"

# Block types that cannot be created via API
SKIP_BLOCK_TYPES = {"child_page", "child_database", "unsupported", "link_to_page"}

# Block types that can have children
PARENT_BLOCK_TYPES = {
    "paragraph", "bulleted_list_item", "numbered_list_item",
    "toggle", "to_do", "quote", "callout",
    "synced_block", "template", "column", "column_list",
    "table", "table_row", "heading_1", "heading_2",
    "heading_3", "heading_4", "tab",
}
```

- [ ] **Step 3: Create empty __init__.py**

```python
# notion-cms/__init__.py
```

- [ ] **Step 4: Create migrate.py with full schema DDL**

```python
# notion-cms/migrate.py
"""Create the notion_cms schema and all tables on B4All-Hub."""
import psycopg2
import sys
from config import SUPABASE_DB_URL

SCHEMA_DDL = """
-- Schema
CREATE SCHEMA IF NOT EXISTS notion_cms;

-- Pages
CREATE TABLE IF NOT EXISTS notion_cms.pages (
  notion_page_id       uuid PRIMARY KEY,
  url                  text,
  public_url           text,
  parent_type          text,
  parent_id            uuid,
  in_trash             boolean DEFAULT false,
  is_archived          boolean DEFAULT false,
  is_locked            boolean DEFAULT false,
  created_time         timestamptz,
  created_by           uuid,
  last_edited_time     timestamptz,
  last_edited_by       uuid,
  icon                 jsonb,
  cover                jsonb,
  title                text NOT NULL,
  hub                  text,
  section              text,
  sub_section          text,
  type                 text,
  status               text,
  owner                text,
  audience             text[],
  topics               text[],
  description          text,
  last_reviewed        date,
  files_and_media      jsonb,
  parent_page_ids      uuid[],
  related_page_ids     uuid[],
  section_page_ids     uuid[],
  block_count          int,
  pulled_at            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pages_hub ON notion_cms.pages (hub);
CREATE INDEX IF NOT EXISTS idx_pages_section ON notion_cms.pages (section);
CREATE INDEX IF NOT EXISTS idx_pages_type ON notion_cms.pages (type);
CREATE INDEX IF NOT EXISTS idx_pages_status ON notion_cms.pages (status);

-- Blocks
CREATE TABLE IF NOT EXISTS notion_cms.blocks (
  notion_block_id      uuid PRIMARY KEY,
  page_id              uuid NOT NULL REFERENCES notion_cms.pages,
  parent_block_id      uuid,
  type                 text NOT NULL,
  sort_order           int NOT NULL,
  depth                int DEFAULT 0,
  has_children         boolean DEFAULT false,
  content              jsonb NOT NULL,
  color                text,
  rich_text_plain      text,
  language             text,
  is_toggleable        boolean,
  checked              boolean,
  caption_plain        text,
  media_type           text,
  media_url            text,
  media_expiry         timestamptz,
  storage_url          text,
  created_time         timestamptz,
  created_by           uuid,
  last_edited_time     timestamptz,
  last_edited_by       uuid,
  in_trash             boolean DEFAULT false,
  pulled_at            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_blocks_page ON notion_cms.blocks (page_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_blocks_type ON notion_cms.blocks (type);
CREATE INDEX IF NOT EXISTS idx_blocks_parent ON notion_cms.blocks (parent_block_id);
CREATE INDEX IF NOT EXISTS idx_blocks_media ON notion_cms.blocks (page_id) WHERE media_url IS NOT NULL;

-- Views
CREATE TABLE IF NOT EXISTS notion_cms.views (
  notion_view_id       uuid PRIMARY KEY,
  database_id          uuid NOT NULL,
  data_source_id       text NOT NULL,
  name                 text NOT NULL,
  type                 text NOT NULL,
  config               jsonb NOT NULL,
  filter_hub           text,
  filter_type          text,
  group_by_property    text,
  is_managed           boolean DEFAULT true,
  pulled_at            timestamptz DEFAULT now(),
  pushed_at            timestamptz
);

-- Comments
CREATE TABLE IF NOT EXISTS notion_cms.comments (
  notion_comment_id    uuid PRIMARY KEY,
  discussion_id        uuid NOT NULL,
  parent_type          text NOT NULL,
  parent_id            uuid NOT NULL,
  rich_text            jsonb NOT NULL,
  plain_text           text,
  attachments          jsonb,
  created_time         timestamptz,
  created_by           uuid,
  last_edited_time     timestamptz,
  display_name         jsonb,
  pulled_at            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_comments_page ON notion_cms.comments (parent_id);
CREATE INDEX IF NOT EXISTS idx_comments_discussion ON notion_cms.comments (discussion_id);

-- Images
CREATE TABLE IF NOT EXISTS notion_cms.images (
  id                   bigserial PRIMARY KEY,
  original_filename    text NOT NULL,
  file_hash            text NOT NULL,
  file_size_bytes      bigint,
  mime_type            text,
  storage_path         text NOT NULL UNIQUE,
  public_url           text NOT NULL,
  hub                  text,
  section              text,
  mapped_page_id       uuid REFERENCES notion_cms.pages,
  mapped_block_id      uuid,
  category             text,
  uploaded_at          timestamptz DEFAULT now(),
  pushed_at            timestamptz
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_images_hash ON notion_cms.images (file_hash);

-- Push Queue
CREATE TABLE IF NOT EXISTS notion_cms.push_queue (
  id                   bigserial PRIMARY KEY,
  page_id              uuid REFERENCES notion_cms.pages,
  block_id             uuid,
  view_id              uuid,
  operation            text NOT NULL,
  payload              jsonb NOT NULL,
  position             jsonb,
  status               text DEFAULT 'pending',
  batch_id             text,
  priority             int DEFAULT 0,
  retry_count          int DEFAULT 0,
  max_retries          int DEFAULT 3,
  error                text,
  error_code           text,
  created_at           timestamptz DEFAULT now(),
  queued_at            timestamptz,
  pushed_at            timestamptz,
  confirmed_at         timestamptz
);

CREATE INDEX IF NOT EXISTS idx_queue_status ON notion_cms.push_queue (status) WHERE status NOT IN ('confirmed', 'failed');
CREATE INDEX IF NOT EXISTS idx_queue_batch ON notion_cms.push_queue (batch_id, priority DESC);
CREATE INDEX IF NOT EXISTS idx_queue_page ON notion_cms.push_queue (page_id);

-- API Constraints Reference
CREATE TABLE IF NOT EXISTS notion_cms.api_constraints (
  key                  text PRIMARY KEY,
  value                text NOT NULL,
  notes                text
);

INSERT INTO notion_cms.api_constraints VALUES
  ('rate_limit_rps',          '3',          'Average requests/second per integration'),
  ('max_blocks_per_append',   '100',        'Max blocks in single PATCH /blocks/{id}/children'),
  ('max_nesting_per_append',  '2',          'Max nesting depth per append request'),
  ('max_payload_bytes',       '500000',     '500 KB max request payload'),
  ('max_rich_text_chars',     '2000',       'Per rich_text object, not per block'),
  ('max_equation_chars',      '1000',       'KaTeX expression limit'),
  ('file_url_expiry_secs',    '3600',       'Notion-hosted file URLs expire in 1 hour'),
  ('max_file_size_paid',      '5368709120', '5 GiB for paid workspaces'),
  ('max_relations_per_prop',  '100',        'Max related pages per relation property'),
  ('max_multiselect_options', '100',        'Max options per multi_select property'),
  ('pagination_max_size',     '100',        'Max results per paginated request'),
  ('max_comment_attachments', '3',          'Max file attachments per comment'),
  ('max_sorts_per_view',      '100',        'Max sort rules on a single view'),
  ('max_filter_nesting',      '2',          'Max compound filter nesting depth')
ON CONFLICT (key) DO NOTHING;
"""


def main():
    print("Connecting to Supabase...")
    conn = psycopg2.connect(SUPABASE_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("Creating notion_cms schema and tables...")
    cur.execute(SCHEMA_DDL)

    # Verify
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'notion_cms'
        ORDER BY table_name
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"Created tables: {', '.join(tables)}")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the migration**

```bash
cd projects/notion/notion-cms
pip install -r requirements.txt
python migrate.py
```

Expected output:
```
Connecting to Supabase...
Creating notion_cms schema and tables...
Created tables: api_constraints, blocks, comments, images, pages, push_queue, views
Done.
```

- [ ] **Step 6: Verify tables exist**

Run via Supabase MCP:
```sql
SELECT table_name, (SELECT count(*) FROM information_schema.columns c WHERE c.table_schema = 'notion_cms' AND c.table_name = t.table_name) AS col_count
FROM information_schema.tables t
WHERE table_schema = 'notion_cms'
ORDER BY table_name;
```

Expected: 7 tables (api_constraints, blocks, comments, images, pages, push_queue, views).

- [ ] **Step 7: Commit**

```bash
git add notion-cms/__init__.py notion-cms/config.py notion-cms/migrate.py notion-cms/requirements.txt
git commit -m "feat(notion-cms): schema migration — 7 tables for pages, blocks, views, comments, images, push_queue"
```

---

## Task 2: Notion API Client

**Files:**
- Create: `notion-cms/notion_client.py`
- Create: `tests/test_notion_client.py`

This wraps the Notion API with rate limiting, retries, and pagination — extracted from `scripts/sync_articles_to_db.py` patterns.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notion_client.py
"""Tests for the Notion API client wrapper."""
import json
import time
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "notion-cms"))

from notion_client import NotionClient


def test_headers_include_auth_and_version():
    """Client builds correct headers from config."""
    with patch.dict(os.environ, {"NOTION_API_KEY": "test-key"}):
        client = NotionClient(api_key="test-key")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer test-key"
    assert "Notion-Version" in headers
    assert headers["Content-Type"] == "application/json"


def test_rate_limit_delay():
    """Client sleeps between requests."""
    client = NotionClient(api_key="fake", rate_limit_delay=0.1)
    with patch("notion_client.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"results": []}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        start = time.time()
        client.request("GET", "/test")
        client.request("GET", "/test")
        elapsed = time.time() - start

    assert elapsed >= 0.1, "Should sleep between requests"


def test_paginate_collects_all_pages():
    """paginate() follows next_cursor until has_more is False."""
    client = NotionClient(api_key="fake", rate_limit_delay=0)

    page1 = {"results": [{"id": "a"}], "has_more": True, "next_cursor": "cur1"}
    page2 = {"results": [{"id": "b"}], "has_more": False, "next_cursor": None}

    with patch.object(client, "request", side_effect=[page1, page2]):
        results = client.paginate("GET", "/blocks/x/children")

    assert len(results) == 2
    assert results[0]["id"] == "a"
    assert results[1]["id"] == "b"


def test_fetch_blocks_recursive():
    """fetch_blocks() recurses into children when has_children is True."""
    client = NotionClient(api_key="fake", rate_limit_delay=0)

    top_level = {
        "results": [{
            "id": "block-1",
            "type": "toggle",
            "has_children": True,
            "toggle": {"rich_text": [], "color": "default"},
            "created_time": "2026-01-01T00:00:00Z",
            "last_edited_time": "2026-01-01T00:00:00Z",
            "created_by": {"id": "user-1"},
            "last_edited_by": {"id": "user-1"},
            "in_trash": False,
        }],
        "has_more": False,
    }
    children = {
        "results": [{
            "id": "block-2",
            "type": "paragraph",
            "has_children": False,
            "paragraph": {"rich_text": [{"plain_text": "hello"}], "color": "default"},
            "created_time": "2026-01-01T00:00:00Z",
            "last_edited_time": "2026-01-01T00:00:00Z",
            "created_by": {"id": "user-1"},
            "last_edited_by": {"id": "user-1"},
            "in_trash": False,
        }],
        "has_more": False,
    }

    with patch.object(client, "request", side_effect=[top_level, children]):
        blocks = client.fetch_blocks("page-1")

    assert len(blocks) == 1
    assert blocks[0]["id"] == "block-1"
    assert len(blocks[0]["toggle"]["children"]) == 1
    assert blocks[0]["toggle"]["children"][0]["id"] == "block-2"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd projects/notion && python -m pytest tests/test_notion_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'notion_client'`

- [ ] **Step 3: Write notion_client.py**

```python
# notion-cms/notion_client.py
"""Rate-limited Notion API client with pagination and block tree traversal."""
import json
import time
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

log = logging.getLogger(__name__)

NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"

# Block types that cannot be created via API
SKIP_BLOCK_TYPES = {"child_page", "child_database", "unsupported", "link_to_page"}

# Block types that can have children
PARENT_BLOCK_TYPES = {
    "paragraph", "bulleted_list_item", "numbered_list_item",
    "toggle", "to_do", "quote", "callout",
    "synced_block", "template", "column", "column_list",
    "table", "table_row", "heading_1", "heading_2",
    "heading_3", "heading_4", "tab",
}


class NotionClient:
    """Notion API wrapper with rate limiting, retries, and pagination."""

    def __init__(self, api_key, rate_limit_delay=0.35, max_retries=5):
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.request_count = 0

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def request(self, method, endpoint, body=None, params=None):
        """Make a single API request with rate limiting and retries."""
        url = f"{NOTION_BASE_URL}{endpoint}"
        if params:
            url += "?" + urlencode(params)

        data = json.dumps(body).encode("utf-8") if body else None
        req = Request(url, data=data, headers=self._headers(), method=method)

        for attempt in range(self.max_retries):
            try:
                time.sleep(self.rate_limit_delay)
                self.request_count += 1
                with urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except HTTPError as e:
                resp_body = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    retry_after = int(e.headers.get("Retry-After", 2))
                    log.warning(f"Rate limited, waiting {retry_after}s (attempt {attempt+1})")
                    time.sleep(retry_after)
                    continue
                elif e.code == 409:
                    log.warning(f"Conflict (409), retrying in 1s (attempt {attempt+1})")
                    time.sleep(1)
                    continue
                else:
                    log.error(f"HTTP {e.code}: {resp_body[:300]}")
                    raise
            except URLError as e:
                log.warning(f"Network error: {e.reason}, retrying in 2s (attempt {attempt+1})")
                time.sleep(2)
                continue

        raise Exception(f"Failed after {self.max_retries} attempts: {method} {endpoint}")

    def paginate(self, method, endpoint, body=None, params=None):
        """Auto-paginate a Notion API endpoint, collecting all results."""
        all_results = []
        params = dict(params or {})
        params["page_size"] = "100"
        has_more = True

        while has_more:
            resp = self.request(method, endpoint, body=body, params=params)
            all_results.extend(resp.get("results", []))
            has_more = resp.get("has_more", False)
            if has_more:
                cursor = resp.get("next_cursor")
                if method == "GET":
                    params["start_cursor"] = cursor
                else:
                    body = body or {}
                    body["start_cursor"] = cursor

        return all_results

    def fetch_blocks(self, page_id, recursive=True):
        """Fetch all blocks from a page with optional recursive children."""
        raw_blocks = self.paginate("GET", f"/blocks/{page_id}/children")
        blocks = []

        for block in raw_blocks:
            block_type = block.get("type")
            if block_type in SKIP_BLOCK_TYPES:
                continue

            if recursive and block.get("has_children") and block_type in PARENT_BLOCK_TYPES:
                children = self.fetch_blocks(block["id"], recursive=True)
                if children and block_type in block:
                    block[block_type]["children"] = children

            blocks.append(block)

        return blocks

    def query_database(self, data_source_id, filter_obj=None):
        """Query all rows from a Notion database with pagination."""
        body = {"page_size": 100}
        if filter_obj:
            body["filter"] = filter_obj
        return self.paginate("POST", f"/data_sources/{data_source_id}/query", body=body)

    def get_page(self, page_id):
        """Retrieve a single page with all properties."""
        return self.request("GET", f"/pages/{page_id}")

    def update_block(self, block_id, payload):
        """Update a single block."""
        return self.request("PATCH", f"/blocks/{block_id}", body=payload)

    def append_blocks(self, parent_id, children, position=None):
        """Append blocks to a parent (page or block). Max 100 per call."""
        body = {"children": children}
        if position:
            body["position"] = position
        return self.request("PATCH", f"/blocks/{parent_id}/children", body=body)

    def delete_block(self, block_id):
        """Soft-delete a block."""
        return self.request("DELETE", f"/blocks/{block_id}")

    def update_page(self, page_id, payload):
        """Update page properties, icon, cover, or lifecycle flags."""
        return self.request("PATCH", f"/pages/{page_id}", body=payload)

    def get_comments(self, block_id):
        """List unresolved comments on a page or block."""
        return self.paginate("GET", f"/comments", params={"block_id": block_id})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd projects/notion && python -m pytest tests/test_notion_client.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add notion-cms/notion_client.py tests/test_notion_client.py
git commit -m "feat(notion-cms): Notion API client with rate limiting, pagination, block tree fetch"
```

---

## Task 3: Block Parser

**Files:**
- Create: `notion-cms/block_parser.py`
- Create: `tests/test_block_parser.py`

Parses raw Notion block JSON into the flat row structure for `notion_cms.blocks`, extracting denormalized fields (color, rich_text_plain, language, media_url, etc.).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_block_parser.py
"""Tests for block parsing — raw Notion JSON → flat row dict."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "notion-cms"))

from block_parser import parse_block, parse_page_properties


def test_parse_paragraph_block():
    raw = {
        "id": "abc-123",
        "type": "paragraph",
        "has_children": False,
        "paragraph": {
            "rich_text": [
                {"plain_text": "Hello ", "type": "text", "text": {"content": "Hello "}},
                {"plain_text": "world", "type": "text", "text": {"content": "world"}},
            ],
            "color": "blue",
        },
        "created_time": "2026-01-15T10:30:00.000Z",
        "last_edited_time": "2026-02-01T08:00:00.000Z",
        "created_by": {"id": "user-1"},
        "last_edited_by": {"id": "user-2"},
        "in_trash": False,
    }
    row = parse_block(raw, page_id="page-1", sort_order=0, depth=0)

    assert row["notion_block_id"] == "abc-123"
    assert row["page_id"] == "page-1"
    assert row["type"] == "paragraph"
    assert row["color"] == "blue"
    assert row["rich_text_plain"] == "Hello world"
    assert row["has_children"] is False
    assert row["sort_order"] == 0
    assert row["depth"] == 0
    assert row["media_type"] is None
    assert row["media_url"] is None
    assert row["content"] == raw["paragraph"]


def test_parse_image_block_external():
    raw = {
        "id": "img-1",
        "type": "image",
        "has_children": False,
        "image": {
            "type": "external",
            "external": {"url": "https://example.com/photo.png"},
            "caption": [{"plain_text": "A photo"}],
        },
        "created_time": "2026-01-01T00:00:00Z",
        "last_edited_time": "2026-01-01T00:00:00Z",
        "created_by": {"id": "u1"},
        "last_edited_by": {"id": "u1"},
        "in_trash": False,
    }
    row = parse_block(raw, page_id="page-2", sort_order=3, depth=0)

    assert row["media_type"] == "external"
    assert row["media_url"] == "https://example.com/photo.png"
    assert row["media_expiry"] is None
    assert row["caption_plain"] == "A photo"


def test_parse_image_block_notion_hosted():
    raw = {
        "id": "img-2",
        "type": "image",
        "has_children": False,
        "image": {
            "type": "file",
            "file": {
                "url": "https://prod-files-secure.s3.us-west-2.amazonaws.com/abc",
                "expiry_time": "2026-04-04T12:00:00.000Z",
            },
            "caption": [],
        },
        "created_time": "2026-01-01T00:00:00Z",
        "last_edited_time": "2026-01-01T00:00:00Z",
        "created_by": {"id": "u1"},
        "last_edited_by": {"id": "u1"},
        "in_trash": False,
    }
    row = parse_block(raw, page_id="page-2", sort_order=4, depth=0)

    assert row["media_type"] == "file"
    assert "s3.us-west-2" in row["media_url"]
    assert row["media_expiry"] == "2026-04-04T12:00:00.000Z"


def test_parse_code_block():
    raw = {
        "id": "code-1",
        "type": "code",
        "has_children": False,
        "code": {
            "rich_text": [{"plain_text": "print('hi')"}],
            "language": "python",
            "caption": [{"plain_text": "Example"}],
        },
        "created_time": "2026-01-01T00:00:00Z",
        "last_edited_time": "2026-01-01T00:00:00Z",
        "created_by": {"id": "u1"},
        "last_edited_by": {"id": "u1"},
        "in_trash": False,
    }
    row = parse_block(raw, page_id="p", sort_order=0, depth=0)

    assert row["language"] == "python"
    assert row["caption_plain"] == "Example"
    assert row["rich_text_plain"] == "print('hi')"


def test_parse_heading_toggleable():
    raw = {
        "id": "h-1",
        "type": "heading_2",
        "has_children": True,
        "heading_2": {
            "rich_text": [{"plain_text": "Overview"}],
            "color": "default",
            "is_toggleable": True,
        },
        "created_time": "2026-01-01T00:00:00Z",
        "last_edited_time": "2026-01-01T00:00:00Z",
        "created_by": {"id": "u1"},
        "last_edited_by": {"id": "u1"},
        "in_trash": False,
    }
    row = parse_block(raw, page_id="p", sort_order=0, depth=0)

    assert row["is_toggleable"] is True
    assert row["rich_text_plain"] == "Overview"


def test_parse_todo_checked():
    raw = {
        "id": "td-1",
        "type": "to_do",
        "has_children": False,
        "to_do": {
            "rich_text": [{"plain_text": "Buy milk"}],
            "checked": True,
            "color": "default",
        },
        "created_time": "2026-01-01T00:00:00Z",
        "last_edited_time": "2026-01-01T00:00:00Z",
        "created_by": {"id": "u1"},
        "last_edited_by": {"id": "u1"},
        "in_trash": False,
    }
    row = parse_block(raw, page_id="p", sort_order=0, depth=0)

    assert row["checked"] is True


def test_parse_page_properties():
    """Extract KB properties from a Notion page object into a flat dict."""
    page = {
        "id": "page-abc",
        "url": "https://www.notion.so/page-abc",
        "public_url": None,
        "parent": {"type": "database_id", "database_id": "db-1"},
        "in_trash": False,
        "archived": False,
        "icon": {"type": "emoji", "emoji": "📄"},
        "cover": None,
        "created_time": "2026-01-01T00:00:00.000Z",
        "created_by": {"id": "user-1"},
        "last_edited_time": "2026-03-15T12:00:00.000Z",
        "last_edited_by": {"id": "user-2"},
        "properties": {
            "Article": {"title": [{"plain_text": "How to Reset a Device"}]},
            "Hub": {"select": {"name": "Engineering"}},
            "Section": {"select": {"name": "Thin Client"}},
            "Sub-section": {"select": None},
            "Type": {"select": {"name": "Guide"}},
            "Status": {"select": {"name": "active"}},
            "Owner": {"select": {"name": "engineering"}},
            "Audience": {"multi_select": [{"name": "engineering"}, {"name": "support"}]},
            "Topics": {"multi_select": [{"name": "troubleshooting"}]},
            "Description": {"rich_text": [{"plain_text": "Steps to factory reset"}]},
            "Last Reviewed": {"date": {"start": "2026-02-01"}},
            "Files & media": {"files": []},
            "Parent": {"relation": [{"id": "parent-page-1"}]},
            "Related back to B4ALL Knowledge Base": {"relation": []},
            "Section Page": {"relation": [{"id": "section-page-1"}]},
        },
    }
    row = parse_page_properties(page)

    assert row["notion_page_id"] == "page-abc"
    assert row["title"] == "How to Reset a Device"
    assert row["hub"] == "Engineering"
    assert row["section"] == "Thin Client"
    assert row["sub_section"] is None
    assert row["type"] == "Guide"
    assert row["status"] == "active"
    assert row["owner"] == "engineering"
    assert row["audience"] == ["engineering", "support"]
    assert row["topics"] == ["troubleshooting"]
    assert row["description"] == "Steps to factory reset"
    assert row["last_reviewed"] == "2026-02-01"
    assert row["parent_page_ids"] == ["parent-page-1"]
    assert row["related_page_ids"] == []
    assert row["section_page_ids"] == ["section-page-1"]
    assert row["icon"] == {"type": "emoji", "emoji": "📄"}
    assert row["cover"] is None
    assert row["parent_type"] == "database_id"
    assert row["parent_id"] == "db-1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd projects/notion && python -m pytest tests/test_block_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'block_parser'`

- [ ] **Step 3: Write block_parser.py**

```python
# notion-cms/block_parser.py
"""Parse raw Notion API JSON into flat row dicts for notion_cms tables."""

# Media block types that have a file/external/file_upload sub-object
MEDIA_BLOCK_TYPES = {"image", "video", "audio", "file", "pdf"}

# Block types that have a caption array
CAPTION_BLOCK_TYPES = {"image", "video", "audio", "file", "pdf", "code", "embed"}


def _extract_plain_text(rich_text_array):
    """Concatenate plain_text from a rich_text array."""
    if not rich_text_array or not isinstance(rich_text_array, list):
        return None
    text = "".join(rt.get("plain_text", "") for rt in rich_text_array)
    return text or None


def _extract_media(block_type, content):
    """Extract media_type, media_url, media_expiry from a media block's content."""
    if block_type not in MEDIA_BLOCK_TYPES:
        return None, None, None

    file_type = content.get("type")  # 'external', 'file', or 'file_upload'
    if not file_type:
        return None, None, None

    file_obj = content.get(file_type, {})
    url = file_obj.get("url")
    expiry = file_obj.get("expiry_time")

    return file_type, url, expiry


def parse_block(raw, page_id, sort_order, depth, parent_block_id=None):
    """Parse a raw Notion block into a flat dict for notion_cms.blocks."""
    block_type = raw.get("type", "unsupported")
    content = raw.get(block_type, {})

    # Denormalized fields
    rich_text_plain = _extract_plain_text(content.get("rich_text"))
    color = content.get("color")
    language = content.get("language") if block_type == "code" else None
    is_toggleable = content.get("is_toggleable") if block_type.startswith("heading_") else None
    checked = content.get("checked") if block_type == "to_do" else None
    caption_plain = _extract_plain_text(content.get("caption")) if block_type in CAPTION_BLOCK_TYPES else None

    # Media extraction
    media_type, media_url, media_expiry = _extract_media(block_type, content)

    return {
        "notion_block_id": raw["id"],
        "page_id": page_id,
        "parent_block_id": parent_block_id,
        "type": block_type,
        "sort_order": sort_order,
        "depth": depth,
        "has_children": raw.get("has_children", False),
        "content": content,
        "color": color,
        "rich_text_plain": rich_text_plain,
        "language": language,
        "is_toggleable": is_toggleable,
        "checked": checked,
        "caption_plain": caption_plain,
        "media_type": media_type,
        "media_url": media_url,
        "media_expiry": media_expiry,
        "storage_url": None,
        "created_time": raw.get("created_time"),
        "created_by": raw.get("created_by", {}).get("id"),
        "last_edited_time": raw.get("last_edited_time"),
        "last_edited_by": raw.get("last_edited_by", {}).get("id"),
        "in_trash": raw.get("in_trash", False),
    }


def flatten_block_tree(blocks, page_id, depth=0, parent_block_id=None):
    """Recursively flatten a nested block tree into a list of row dicts.

    Each block's children (if any) are stored inside its content JSON
    AND flattened into separate rows with incremented depth.
    """
    rows = []
    for sort_order, block in enumerate(blocks):
        row = parse_block(block, page_id, sort_order, depth, parent_block_id)
        rows.append(row)

        # Recurse into children if present
        block_type = block.get("type", "")
        content = block.get(block_type, {})
        children = content.get("children", [])
        if children:
            child_rows = flatten_block_tree(
                children, page_id,
                depth=depth + 1,
                parent_block_id=block["id"],
            )
            rows.extend(child_rows)

    return rows


def _select_value(props, key):
    """Extract a select property value (name string or None)."""
    prop = props.get(key, {})
    sel = prop.get("select")
    return sel["name"] if sel else None


def _multi_select_values(props, key):
    """Extract a multi_select property as a list of name strings."""
    prop = props.get(key, {})
    items = prop.get("multi_select", [])
    return [item["name"] for item in items]


def _relation_ids(props, key):
    """Extract relation property as a list of page ID strings."""
    prop = props.get(key, {})
    items = prop.get("relation", [])
    return [item["id"] for item in items]


def parse_page_properties(page):
    """Parse a raw Notion page object into a flat dict for notion_cms.pages."""
    props = page.get("properties", {})

    # Title
    title_prop = props.get("Article", {})
    title_items = title_prop.get("title", [])
    title = title_items[0]["plain_text"] if title_items else "(untitled)"

    # Description
    desc_prop = props.get("Description", {})
    desc_items = desc_prop.get("rich_text", [])
    description = desc_items[0]["plain_text"] if desc_items else None

    # Date
    date_prop = props.get("Last Reviewed", {})
    date_obj = date_prop.get("date")
    last_reviewed = date_obj["start"] if date_obj else None

    # Files
    files_prop = props.get("Files & media", {})
    files_list = files_prop.get("files", [])

    # Parent
    parent = page.get("parent", {})
    parent_type = parent.get("type")
    parent_id = parent.get(parent_type) if parent_type else None

    return {
        "notion_page_id": page["id"],
        "url": page.get("url"),
        "public_url": page.get("public_url"),
        "parent_type": parent_type,
        "parent_id": parent_id,
        "in_trash": page.get("in_trash", False),
        "is_archived": page.get("archived", False) or page.get("is_archived", False),
        "is_locked": page.get("is_locked", False),
        "created_time": page.get("created_time"),
        "created_by": page.get("created_by", {}).get("id"),
        "last_edited_time": page.get("last_edited_time"),
        "last_edited_by": page.get("last_edited_by", {}).get("id"),
        "icon": page.get("icon"),
        "cover": page.get("cover"),
        "title": title,
        "hub": _select_value(props, "Hub"),
        "section": _select_value(props, "Section"),
        "sub_section": _select_value(props, "Sub-section"),
        "type": _select_value(props, "Type"),
        "status": _select_value(props, "Status"),
        "owner": _select_value(props, "Owner"),
        "audience": _multi_select_values(props, "Audience"),
        "topics": _multi_select_values(props, "Topics"),
        "description": description,
        "last_reviewed": last_reviewed,
        "files_and_media": files_list if files_list else None,
        "parent_page_ids": _relation_ids(props, "Parent"),
        "related_page_ids": _relation_ids(props, "Related back to B4ALL Knowledge Base"),
        "section_page_ids": _relation_ids(props, "Section Page"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd projects/notion && python -m pytest tests/test_block_parser.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add notion-cms/block_parser.py tests/test_block_parser.py
git commit -m "feat(notion-cms): block parser — raw Notion JSON to flat row dicts with denormalized fields"
```

---

## Task 4: Media Handler

**Files:**
- Create: `notion-cms/media_handler.py`
- Create: `tests/test_media_handler.py`

Downloads Notion-hosted media (before 1-hour URL expiry) and uploads to Supabase Storage.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_media_handler.py
"""Tests for media download and Supabase Storage upload."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "notion-cms"))

from media_handler import build_storage_path, classify_image


def test_build_storage_path():
    path = build_storage_path("photo.png", hub="Products", section="LiveScan")
    assert path == "products/livescan/photo.png"


def test_build_storage_path_no_section():
    path = build_storage_path("logo.svg", hub="Branding", section=None)
    assert path == "branding/logo.svg"


def test_build_storage_path_sanitizes():
    path = build_storage_path("My File (1).png", hub="Customer Success", section="Applicant Support")
    assert " " not in path
    assert "(" not in path
    assert path == "customer-success/applicant-support/my-file-1.png"


def test_classify_image_product():
    assert classify_image("img-crossmatch-500p.png") == "product"


def test_classify_image_screenshot():
    assert classify_image("cms-screenshot-1.png") == "screenshot"


def test_classify_image_icon():
    assert classify_image("icn-checkmark.svg") == "icon"


def test_classify_image_hero():
    assert classify_image("hero-bg-checks-image.jpg") == "hero"


def test_classify_image_fallback():
    assert classify_image("random-name.png") == "other"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd projects/notion && python -m pytest tests/test_media_handler.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write media_handler.py**

```python
# notion-cms/media_handler.py
"""Download Notion-hosted media, upload to Supabase Storage, manage image registry."""
import hashlib
import logging
import os
import re
import requests
from urllib.request import urlopen

log = logging.getLogger(__name__)

SUPABASE_PROJECT_URL = os.environ.get("SUPABASE_PROJECT_URL", "https://dozjdswqnzqwvieqvwpe.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = "kb-images"


def _sanitize(name):
    """Lowercase, replace spaces/parens with hyphens, collapse multiple hyphens."""
    name = name.lower().strip()
    name = re.sub(r"[^\w.\-]", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")
    return name


def build_storage_path(filename, hub=None, section=None):
    """Build a clean storage path: {hub}/{section}/{filename}."""
    parts = []
    if hub:
        parts.append(_sanitize(hub))
    if section:
        parts.append(_sanitize(section))
    parts.append(_sanitize(filename))
    return "/".join(parts)


def classify_image(filename):
    """Classify an image by filename pattern."""
    fn = filename.lower()
    if fn.startswith("icn-") or fn.startswith("icn_") or fn.startswith("icon-"):
        return "icon"
    if fn.startswith("hero-") or fn.startswith("hero_") or "hero" in fn:
        return "hero"
    if "screenshot" in fn or fn.startswith("cms-screenshot"):
        return "screenshot"
    if fn.startswith("img-") or fn.startswith("img_"):
        return "product"
    if fn.startswith("card-"):
        return "product"
    if fn.startswith("picture") or fn.startswith("image"):
        return "procedure"
    return "other"


def file_hash(filepath):
    """Compute MD5 hash of a local file."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def bytes_hash(data):
    """Compute MD5 hash of bytes."""
    return hashlib.md5(data).hexdigest()


def download_notion_file(url):
    """Download a file from a Notion-hosted URL (before it expires). Returns bytes."""
    log.info(f"Downloading: {url[:80]}...")
    resp = urlopen(url, timeout=30)
    return resp.read()


def upload_to_storage(data, storage_path, content_type="application/octet-stream"):
    """Upload bytes to Supabase Storage. Returns public URL."""
    url = f"{SUPABASE_PROJECT_URL}/storage/v1/object/{STORAGE_BUCKET}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()

    public_url = f"{SUPABASE_PROJECT_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_path}"
    log.info(f"Uploaded: {storage_path} → {public_url}")
    return public_url


def upload_local_file(filepath, storage_path):
    """Upload a local file to Supabase Storage. Returns (public_url, file_hash, file_size)."""
    with open(filepath, "rb") as f:
        data = f.read()

    # Guess content type
    ext = os.path.splitext(filepath)[1].lower()
    content_types = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml", ".webp": "image/webp", ".gif": "image/gif",
    }
    ct = content_types.get(ext, "application/octet-stream")

    public_url = upload_to_storage(data, storage_path, content_type=ct)
    return public_url, bytes_hash(data), len(data)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd projects/notion && python -m pytest tests/test_media_handler.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add notion-cms/media_handler.py tests/test_media_handler.py
git commit -m "feat(notion-cms): media handler — download Notion files, upload to Supabase Storage"
```

---

## Task 5: Pull Script — Pages

**Files:**
- Create: `notion-cms/pull.py`
- Create: `tests/test_pull.py`

Pulls all 715 KB pages (properties only, no blocks yet) into `notion_cms.pages`.

- [ ] **Step 1: Write pull.py with page pulling**

```python
# notion-cms/pull.py
"""One-time pull: Notion KB database → notion_cms schema in Supabase."""
import json
import logging
import os
import sys
import time
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

from config import SUPABASE_DB_URL, DATA_SOURCE_ID, DATABASE_ID
from notion_client import NotionClient
from block_parser import parse_page_properties, flatten_block_tree

# ── Logging ───────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"pull_{timestamp}.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def get_client():
    return NotionClient(api_key=os.environ["NOTION_API_KEY"])


def get_db():
    conn = psycopg2.connect(SUPABASE_DB_URL)
    conn.autocommit = True
    return conn


# ── Page Pull ─────────────────────────────────────────────────────
def pull_pages(client, conn):
    """Query all KB database rows and insert into notion_cms.pages."""
    log.info("Querying KB database for all pages...")
    raw_pages = client.query_database(DATA_SOURCE_ID)
    log.info(f"Fetched {len(raw_pages)} pages from Notion")

    rows = []
    for page in raw_pages:
        row = parse_page_properties(page)
        rows.append(row)

    if not rows:
        log.warning("No pages fetched!")
        return 0

    cur = conn.cursor()

    # Truncate and re-insert (one-time pull)
    cur.execute("TRUNCATE notion_cms.pages CASCADE")

    columns = [
        "notion_page_id", "url", "public_url", "parent_type", "parent_id",
        "in_trash", "is_archived", "is_locked",
        "created_time", "created_by", "last_edited_time", "last_edited_by",
        "icon", "cover",
        "title", "hub", "section", "sub_section", "type", "status", "owner",
        "audience", "topics", "description", "last_reviewed",
        "files_and_media",
        "parent_page_ids", "related_page_ids", "section_page_ids",
    ]

    values = []
    for r in rows:
        values.append((
            r["notion_page_id"], r["url"], r["public_url"],
            r["parent_type"], r["parent_id"],
            r["in_trash"], r["is_archived"], r["is_locked"],
            r["created_time"], r["created_by"],
            r["last_edited_time"], r["last_edited_by"],
            json.dumps(r["icon"]) if r["icon"] else None,
            json.dumps(r["cover"]) if r["cover"] else None,
            r["title"], r["hub"], r["section"], r["sub_section"],
            r["type"], r["status"], r["owner"],
            r["audience"] or None, r["topics"] or None,
            r["description"], r["last_reviewed"],
            json.dumps(r["files_and_media"]) if r["files_and_media"] else None,
            r["parent_page_ids"] or None,
            r["related_page_ids"] or None,
            r["section_page_ids"] or None,
        ))

    insert_sql = f"""
        INSERT INTO notion_cms.pages ({', '.join(columns)})
        VALUES %s
    """
    template = "(" + ", ".join(["%s"] * len(columns)) + ")"
    execute_values(cur, insert_sql, values, template=template)
    cur.close()

    log.info(f"Inserted {len(values)} pages into notion_cms.pages")
    return len(values)


# ── Block Pull ────────────────────────────────────────────────────
def pull_blocks_for_page(client, conn, page_id, title):
    """Fetch all blocks for a single page and insert into notion_cms.blocks."""
    blocks = client.fetch_blocks(page_id, recursive=True)
    if not blocks:
        return 0

    rows = flatten_block_tree(blocks, page_id)

    cur = conn.cursor()
    columns = [
        "notion_block_id", "page_id", "parent_block_id",
        "type", "sort_order", "depth", "has_children",
        "content",
        "color", "rich_text_plain", "language", "is_toggleable", "checked", "caption_plain",
        "media_type", "media_url", "media_expiry", "storage_url",
        "created_time", "created_by", "last_edited_time", "last_edited_by", "in_trash",
    ]

    values = []
    for r in rows:
        values.append((
            r["notion_block_id"], r["page_id"], r["parent_block_id"],
            r["type"], r["sort_order"], r["depth"], r["has_children"],
            json.dumps(r["content"]),
            r["color"], r["rich_text_plain"], r["language"],
            r["is_toggleable"], r["checked"], r["caption_plain"],
            r["media_type"], r["media_url"], r["media_expiry"], r["storage_url"],
            r["created_time"], r["created_by"],
            r["last_edited_time"], r["last_edited_by"], r["in_trash"],
        ))

    insert_sql = f"""
        INSERT INTO notion_cms.blocks ({', '.join(columns)})
        VALUES %s
        ON CONFLICT (notion_block_id) DO NOTHING
    """
    template = "(" + ", ".join(["%s"] * len(columns)) + ")"
    execute_values(cur, insert_sql, values, template=template)
    cur.close()

    return len(values)


def pull_all_blocks(client, conn):
    """Pull blocks for every page in notion_cms.pages."""
    cur = conn.cursor()
    cur.execute("SELECT notion_page_id, title FROM notion_cms.pages ORDER BY hub, section, title")
    pages = cur.fetchall()
    cur.close()

    # Clear existing blocks
    cur = conn.cursor()
    cur.execute("TRUNCATE notion_cms.blocks")
    cur.close()

    total_blocks = 0
    for i, (page_id, title) in enumerate(pages):
        log.info(f"[{i+1}/{len(pages)}] Pulling blocks for: {title}")
        try:
            count = pull_blocks_for_page(client, conn, page_id, title)
            total_blocks += count
            log.info(f"  → {count} blocks")
        except Exception as e:
            log.error(f"  FAILED: {e}")

    log.info(f"Total blocks pulled: {total_blocks}")

    # Update block counts on pages
    cur = conn.cursor()
    cur.execute("""
        UPDATE notion_cms.pages p
        SET block_count = (SELECT count(*) FROM notion_cms.blocks b WHERE b.page_id = p.notion_page_id)
    """)
    cur.close()

    return total_blocks


# ── View Pull ─────────────────────────────────────────────────────
def pull_views(client, conn):
    """Pull all view configurations for the KB database."""
    log.info("Fetching database to get view URLs...")
    db = client.request("GET", f"/databases/{DATABASE_ID}")

    # The MCP fetch showed us the views — we need to get them via the views API
    # List views for the database
    views_resp = client.request("GET", "/views", params={"database_id": DATABASE_ID})
    views = views_resp.get("results", [])
    log.info(f"Found {len(views)} views")

    cur = conn.cursor()
    cur.execute("TRUNCATE notion_cms.views")

    for view in views:
        # Extract filter hub/type for denormalization
        config = view.get("view", {})
        filter_hub = None
        filter_type = None
        group_by_prop = None

        adv_filter = config.get("advancedFilter", {})
        for f in adv_filter.get("filters", []):
            if isinstance(f, dict):
                prop = f.get("property")
                val = f.get("value", {})
                if prop == "Hub" and isinstance(val, dict):
                    filter_hub = val.get("value")
                elif prop == "Type" and isinstance(val, dict):
                    filter_type = val.get("value")

        gb = config.get("groupBy", {})
        if gb:
            group_by_prop = gb.get("property")

        cur.execute("""
            INSERT INTO notion_cms.views
                (notion_view_id, database_id, data_source_id, name, type, config,
                 filter_hub, filter_type, group_by_property)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            view["id"], DATABASE_ID, DATA_SOURCE_ID,
            config.get("name", "Untitled"),
            config.get("type", "table"),
            json.dumps(config),
            filter_hub, filter_type, group_by_prop,
        ))

    cur.close()
    log.info(f"Inserted {len(views)} views into notion_cms.views")
    return len(views)


# ── Comment Pull ──────────────────────────────────────────────────
def pull_comments(client, conn):
    """Pull comments for all pages."""
    cur = conn.cursor()
    cur.execute("SELECT notion_page_id, title FROM notion_cms.pages")
    pages = cur.fetchall()
    cur.execute("TRUNCATE notion_cms.comments")
    cur.close()

    total = 0
    for i, (page_id, title) in enumerate(pages):
        try:
            comments = client.get_comments(page_id)
            if not comments:
                continue

            cur = conn.cursor()
            for c in comments:
                rt = c.get("rich_text", [])
                plain = "".join(r.get("plain_text", "") for r in rt)
                cur.execute("""
                    INSERT INTO notion_cms.comments
                        (notion_comment_id, discussion_id, parent_type, parent_id,
                         rich_text, plain_text, attachments,
                         created_time, created_by, last_edited_time, display_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    c["id"], c.get("discussion_id"),
                    c.get("parent", {}).get("type", "page_id"),
                    page_id,
                    json.dumps(rt), plain,
                    json.dumps(c.get("attachments")) if c.get("attachments") else None,
                    c.get("created_time"), c.get("created_by", {}).get("id"),
                    c.get("last_edited_time"),
                    json.dumps(c.get("display_name")) if c.get("display_name") else None,
                ))
            cur.close()
            total += len(comments)

            if comments:
                log.info(f"  [{i+1}/{len(pages)}] {title}: {len(comments)} comments")
        except Exception as e:
            log.warning(f"  [{i+1}/{len(pages)}] Comments failed for {title}: {e}")

    log.info(f"Total comments pulled: {total}")
    return total


# ── Main ──────────────────────────────────────────────────────────
def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"

    client = get_client()
    conn = get_db()

    start = time.time()

    if what in ("all", "pages"):
        pull_pages(client, conn)

    if what in ("all", "blocks"):
        pull_all_blocks(client, conn)

    if what in ("all", "views"):
        pull_views(client, conn)

    if what in ("all", "comments"):
        pull_comments(client, conn)

    elapsed = time.time() - start
    log.info(f"Pull complete in {elapsed:.0f}s ({client.request_count} API requests)")
    conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run pages-only pull**

```bash
cd projects/notion/notion-cms
python pull.py pages
```

Expected output:
```
Querying KB database for all pages...
Fetched 715 pages from Notion
Inserted 715 pages into notion_cms.pages
Pull complete in ~240s (8 API requests)
```

- [ ] **Step 3: Verify pages in Supabase**

```sql
SELECT hub, count(*), count(DISTINCT section) AS sections
FROM notion_cms.pages
GROUP BY hub ORDER BY count(*) DESC;
```

Expected: ~10 hubs, counts matching the CLAUDE.md article counts.

- [ ] **Step 4: Commit**

```bash
git add notion-cms/pull.py
git commit -m "feat(notion-cms): pull script — pages, blocks, views, comments from Notion to Supabase"
```

---

## Task 6: Pull Blocks

**Files:**
- Modify: `notion-cms/pull.py` (already written — just execute the blocks phase)

- [ ] **Step 1: Run blocks pull**

This is the big one — ~715 pages x recursive block fetch. Expect ~15-20 minutes.

```bash
cd projects/notion/notion-cms
python pull.py blocks
```

Expected output (streaming):
```
[1/715] Pulling blocks for: Applicant Refund Policy
  → 23 blocks
[2/715] Pulling blocks for: Background Check Status Lookup
  → 45 blocks
...
[715/715] Pulling blocks for: Zendesk Integration Guide
  → 12 blocks
Total blocks pulled: ~37000
Pull complete in ~900s (~2500 API requests)
```

- [ ] **Step 2: Verify blocks in Supabase**

```sql
-- Block count by type
SELECT type, count(*) FROM notion_cms.blocks GROUP BY type ORDER BY count(*) DESC LIMIT 20;

-- Pages with most blocks
SELECT p.title, p.hub, p.block_count
FROM notion_cms.pages p ORDER BY block_count DESC LIMIT 10;

-- Media blocks (images/files to re-host)
SELECT type, media_type, count(*)
FROM notion_cms.blocks WHERE media_url IS NOT NULL
GROUP BY type, media_type;
```

- [ ] **Step 3: Commit verification results as a log note**

```bash
git add -A && git commit -m "data: pull complete — pages and blocks snapshot from Notion"
```

---

## Task 7: Pull Views & Comments

**Files:**
- Modify: `notion-cms/pull.py` (already written — execute views + comments phases)

- [ ] **Step 1: Pull views**

```bash
cd projects/notion/notion-cms
python pull.py views
```

Expected: `Inserted 13 views into notion_cms.views`

- [ ] **Step 2: Pull comments**

```bash
cd projects/notion/notion-cms
python pull.py comments
```

Expected: Comments pulled for pages that have them.

- [ ] **Step 3: Verify**

```sql
SELECT name, type, filter_hub FROM notion_cms.views ORDER BY name;
SELECT count(*) FROM notion_cms.comments;
```

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "data: views and comments pull complete"
```

---

## Task 8: Supabase Storage Setup & Image Upload

**Files:**
- Create: `notion-cms/storage.py`

Deduplicates branding-assets, uploads to Supabase Storage, registers in `notion_cms.images`.

- [ ] **Step 1: Create the kb-images bucket**

Run via Supabase dashboard or REST API:
```bash
curl -X POST "https://dozjdswqnzqwvieqvwpe.supabase.co/storage/v1/bucket" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"id": "kb-images", "name": "kb-images", "public": true}'
```

- [ ] **Step 2: Write storage.py**

```python
# notion-cms/storage.py
"""Upload branding-assets images to Supabase Storage and register in notion_cms.images."""
import json
import logging
import os
import sys
from pathlib import Path

import psycopg2

from config import SUPABASE_DB_URL
from media_handler import (
    build_storage_path, classify_image, file_hash,
    upload_local_file,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s")
log = logging.getLogger(__name__)

BRANDING_DIR = os.path.join(os.path.dirname(__file__), "..", "branding-assets")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}


def find_all_images(base_dir):
    """Find all image files recursively, return list of Path objects."""
    images = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if Path(f).suffix.lower() in IMAGE_EXTENSIONS:
                images.append(Path(root) / f)
    return images


def deduplicate(images):
    """Deduplicate images by MD5 hash, keeping the first occurrence."""
    seen = {}
    unique = []
    for img in sorted(images):
        h = file_hash(str(img))
        if h not in seen:
            seen[h] = img
            unique.append((img, h))
        else:
            log.debug(f"Duplicate skipped: {img.name} (same as {seen[h].name})")
    return unique


def main():
    conn = psycopg2.connect(SUPABASE_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Find and deduplicate
    all_images = find_all_images(BRANDING_DIR)
    log.info(f"Found {len(all_images)} total images in branding-assets")

    unique = deduplicate(all_images)
    log.info(f"Deduplicated to {len(unique)} unique images")

    # Check what's already uploaded
    cur.execute("SELECT file_hash FROM notion_cms.images")
    existing_hashes = {r[0] for r in cur.fetchall()}
    to_upload = [(img, h) for img, h in unique if h not in existing_hashes]
    log.info(f"{len(to_upload)} new images to upload ({len(existing_hashes)} already in DB)")

    uploaded = 0
    failed = 0
    for img_path, h in to_upload:
        category = classify_image(img_path.name)
        # Use category as hub-level grouping for branding assets
        storage_path = build_storage_path(img_path.name, hub=category)

        try:
            public_url, _, file_size = upload_local_file(str(img_path), storage_path)

            ext = img_path.suffix.lower()
            mime_types = {
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".svg": "image/svg+xml", ".webp": "image/webp", ".gif": "image/gif",
            }

            cur.execute("""
                INSERT INTO notion_cms.images
                    (original_filename, file_hash, file_size_bytes, mime_type,
                     storage_path, public_url, category)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_hash) DO NOTHING
            """, (
                img_path.name, h, file_size, mime_types.get(ext),
                storage_path, public_url, category,
            ))
            uploaded += 1
            log.info(f"[{uploaded}/{len(to_upload)}] {img_path.name} → {storage_path}")

        except Exception as e:
            failed += 1
            log.error(f"Failed: {img_path.name}: {e}")

    cur.close()
    conn.close()
    log.info(f"Done: {uploaded} uploaded, {failed} failed, {len(existing_hashes)} already existed")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the upload**

```bash
cd projects/notion/notion-cms
python storage.py
```

Expected: ~284 unique images uploaded, registered in `notion_cms.images`.

- [ ] **Step 4: Verify**

```sql
SELECT category, count(*), sum(file_size_bytes) / 1024 / 1024 AS mb
FROM notion_cms.images
GROUP BY category ORDER BY count(*) DESC;
```

- [ ] **Step 5: Commit**

```bash
git add notion-cms/storage.py
git commit -m "feat(notion-cms): storage upload — deduplicate branding-assets, upload to Supabase Storage"
```

---

## Task 9: Re-Host Notion Media

**Files:**
- Modify: `notion-cms/pull.py` (add a `media` subcommand)

Downloads Notion-hosted media from blocks (where `media_type = 'file'`) before URLs expire, uploads to Supabase Storage, updates `storage_url` on blocks.

- [ ] **Step 1: Add media re-hosting function to pull.py**

Add this function after the `pull_comments` function in `pull.py`:

```python
# Add to pull.py after pull_comments()

def rehost_media(conn):
    """Download Notion-hosted media and re-host in Supabase Storage."""
    cur = conn.cursor()
    cur.execute("""
        SELECT notion_block_id, page_id, type, media_url, media_expiry
        FROM notion_cms.blocks
        WHERE media_type = 'file' AND storage_url IS NULL AND media_url IS NOT NULL
    """)
    blocks = cur.fetchall()
    cur.close()

    if not blocks:
        log.info("No Notion-hosted media to re-host")
        return 0

    log.info(f"Re-hosting {len(blocks)} Notion-hosted media files...")
    from media_handler import download_notion_file, upload_to_storage, bytes_hash, build_storage_path

    success = 0
    for i, (block_id, page_id, block_type, media_url, expiry) in enumerate(blocks):
        try:
            data = download_notion_file(media_url)
            h = bytes_hash(data)

            # Determine extension from URL or content type
            ext = ".bin"
            for e in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".mp4", ".mp3"]:
                if e in media_url.lower():
                    ext = e
                    break

            filename = f"{block_id[:8]}{ext}"
            storage_path = build_storage_path(filename, hub="notion-media", section=block_type)

            content_types = {
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".svg": "image/svg+xml", ".webp": "image/webp", ".gif": "image/gif",
                ".pdf": "application/pdf", ".mp4": "video/mp4", ".mp3": "audio/mpeg",
            }
            ct = content_types.get(ext, "application/octet-stream")

            public_url = upload_to_storage(data, storage_path, content_type=ct)

            cur = conn.cursor()
            cur.execute("""
                UPDATE notion_cms.blocks SET storage_url = %s
                WHERE notion_block_id = %s
            """, (public_url, block_id))
            cur.close()

            success += 1
            log.info(f"  [{success}/{len(blocks)}] {block_type} {block_id[:8]} → {storage_path}")

        except Exception as e:
            log.error(f"  Failed {block_id[:8]}: {e}")

    log.info(f"Re-hosted {success}/{len(blocks)} media files")
    return success
```

Update the `main()` function to include the `media` subcommand:

```python
# In main(), add:
    if what in ("all", "media"):
        rehost_media(conn)
```

- [ ] **Step 2: Run media re-hosting**

```bash
cd projects/notion/notion-cms
python pull.py media
```

Expected: Downloads and re-hosts any Notion-hosted media found in blocks.

- [ ] **Step 3: Verify**

```sql
SELECT count(*) AS total_media,
       count(storage_url) AS rehosted,
       count(*) - count(storage_url) AS remaining
FROM notion_cms.blocks
WHERE media_url IS NOT NULL;
```

- [ ] **Step 4: Commit**

```bash
git add notion-cms/pull.py
git commit -m "feat(notion-cms): re-host Notion media — download expiring URLs, upload to Supabase Storage"
```

---

## Task 10: Push Script

**Files:**
- Create: `notion-cms/push.py`
- Create: `tests/test_push.py`

Processes `push_queue` items and executes them against the Notion API.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_push.py
"""Tests for the push queue processor."""
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "notion-cms"))

from push import build_api_call


def test_build_update_block():
    item = {
        "id": 1, "page_id": "p1", "block_id": "b1", "view_id": None,
        "operation": "update_block",
        "payload": {"callout": {"color": "blue_background"}},
        "position": None,
    }
    method, endpoint, body = build_api_call(item)
    assert method == "PATCH"
    assert endpoint == "/blocks/b1"
    assert body == {"callout": {"color": "blue_background"}}


def test_build_append_blocks():
    item = {
        "id": 2, "page_id": "p1", "block_id": None, "view_id": None,
        "operation": "append_blocks",
        "payload": {"children": [{"type": "paragraph"}]},
        "position": {"type": "end"},
    }
    method, endpoint, body = build_api_call(item)
    assert method == "PATCH"
    assert endpoint == "/blocks/p1/children"
    assert body["children"] == [{"type": "paragraph"}]
    assert body["position"] == {"type": "end"}


def test_build_delete_block():
    item = {
        "id": 3, "page_id": "p1", "block_id": "b1", "view_id": None,
        "operation": "delete_block",
        "payload": {},
        "position": None,
    }
    method, endpoint, body = build_api_call(item)
    assert method == "DELETE"
    assert endpoint == "/blocks/b1"
    assert body is None


def test_build_update_properties():
    item = {
        "id": 4, "page_id": "p1", "block_id": None, "view_id": None,
        "operation": "update_properties",
        "payload": {"properties": {"Status": {"select": {"name": "active"}}}},
        "position": None,
    }
    method, endpoint, body = build_api_call(item)
    assert method == "PATCH"
    assert endpoint == "/pages/p1"
    assert "properties" in body


def test_build_create_view():
    item = {
        "id": 5, "page_id": None, "block_id": None, "view_id": None,
        "operation": "create_view",
        "payload": {"database_id": "db1", "type": "table", "name": "Test"},
        "position": None,
    }
    method, endpoint, body = build_api_call(item)
    assert method == "POST"
    assert endpoint == "/views"


def test_build_update_view():
    item = {
        "id": 6, "page_id": None, "block_id": None, "view_id": "v1",
        "operation": "update_view",
        "payload": {"name": "Updated"},
        "position": None,
    }
    method, endpoint, body = build_api_call(item)
    assert method == "PATCH"
    assert endpoint == "/views/v1"


def test_build_insert_image():
    item = {
        "id": 7, "page_id": "p1", "block_id": None, "view_id": None,
        "operation": "insert_image",
        "payload": {"children": [{"type": "image", "image": {"type": "external", "external": {"url": "https://x.com/img.png"}}}]},
        "position": {"type": "after_block", "after_block": {"id": "b-prev"}},
    }
    method, endpoint, body = build_api_call(item)
    assert method == "PATCH"
    assert endpoint == "/blocks/p1/children"
    assert body["position"]["type"] == "after_block"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd projects/notion && python -m pytest tests/test_push.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write push.py**

```python
# notion-cms/push.py
"""Process notion_cms.push_queue → Notion API calls."""
import json
import logging
import os
import sys
import time
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from config import SUPABASE_DB_URL
from notion_client import NotionClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def build_api_call(item):
    """Map a push_queue row to (method, endpoint, body)."""
    op = item["operation"]
    page_id = item["page_id"]
    block_id = item["block_id"]
    view_id = item["view_id"]
    payload = item["payload"]
    position = item["position"]

    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(position, str):
        position = json.loads(position)

    if op == "update_block":
        return "PATCH", f"/blocks/{block_id}", payload

    elif op == "append_blocks":
        body = dict(payload)
        if position:
            body["position"] = position
        return "PATCH", f"/blocks/{page_id}/children", body

    elif op == "insert_image":
        body = dict(payload)
        if position:
            body["position"] = position
        return "PATCH", f"/blocks/{page_id}/children", body

    elif op == "delete_block":
        return "DELETE", f"/blocks/{block_id}", None

    elif op in ("update_properties", "update_icon", "update_cover",
                "lock_page", "trash_page", "archive_page"):
        return "PATCH", f"/pages/{page_id}", payload

    elif op == "replace_media_url":
        return "PATCH", f"/blocks/{block_id}", payload

    elif op == "create_view":
        return "POST", "/views", payload

    elif op == "update_view":
        return "PATCH", f"/views/{view_id}", payload

    elif op == "delete_view":
        return "DELETE", f"/views/{view_id}", None

    elif op == "create_comment":
        return "POST", "/comments", payload

    elif op == "replace_page_content":
        # This is a compound operation — handled specially in process_queue
        return "REPLACE_PAGE", page_id, payload

    else:
        raise ValueError(f"Unknown operation: {op}")


def process_queue(batch_id=None, limit=None, dry_run=False):
    """Process pending items in the push queue."""
    client = NotionClient(api_key=os.environ["NOTION_API_KEY"])
    conn = psycopg2.connect(SUPABASE_DB_URL)
    conn.autocommit = True

    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT * FROM notion_cms.push_queue
        WHERE status = 'pending'
    """
    params = []
    if batch_id:
        query += " AND batch_id = %s"
        params.append(batch_id)
    query += " ORDER BY priority DESC, id ASC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)

    cur.execute(query, params)
    items = cur.fetchall()
    cur.close()

    log.info(f"Processing {len(items)} queue items" + (f" (batch: {batch_id})" if batch_id else ""))

    success = 0
    failed = 0

    for item in items:
        item_id = item["id"]
        op = item["operation"]

        if dry_run:
            method, endpoint, body = build_api_call(item)
            log.info(f"  [DRY RUN] #{item_id} {op}: {method} {endpoint}")
            continue

        # Mark as pushing
        cur = conn.cursor()
        cur.execute("UPDATE notion_cms.push_queue SET status = 'pushing', queued_at = now() WHERE id = %s", (item_id,))
        cur.close()

        try:
            if op == "replace_page_content":
                # Compound: delete all blocks, then re-append
                page_id = item["page_id"]
                payload = item["payload"] if isinstance(item["payload"], dict) else json.loads(item["payload"])

                # Delete existing blocks
                existing = client.paginate("GET", f"/blocks/{page_id}/children")
                for block in existing:
                    client.delete_block(block["id"])

                # Append new blocks in batches of 100
                children = payload.get("children", [])
                for i in range(0, len(children), 100):
                    batch = children[i:i+100]
                    client.append_blocks(page_id, batch)

                log.info(f"  #{item_id} replace_page_content: deleted {len(existing)}, appended {len(children)}")
            else:
                method, endpoint, body = build_api_call(item)
                client.request(method, endpoint, body=body)
                log.info(f"  #{item_id} {op}: OK")

            cur = conn.cursor()
            cur.execute("""
                UPDATE notion_cms.push_queue
                SET status = 'pushed', pushed_at = now()
                WHERE id = %s
            """, (item_id,))
            cur.close()
            success += 1

        except Exception as e:
            log.error(f"  #{item_id} {op}: FAILED — {e}")
            cur = conn.cursor()
            cur.execute("""
                UPDATE notion_cms.push_queue
                SET status = 'failed', error = %s, retry_count = retry_count + 1
                WHERE id = %s
            """, (str(e)[:500], item_id))
            cur.close()
            failed += 1

    conn.close()
    log.info(f"Done: {success} pushed, {failed} failed ({client.request_count} API requests)")
    return success, failed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Process notion_cms push queue")
    parser.add_argument("--batch", help="Only process items with this batch_id")
    parser.add_argument("--limit", type=int, help="Max items to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--retry-failed", action="store_true", help="Re-queue failed items")
    args = parser.parse_args()

    if args.retry_failed:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            UPDATE notion_cms.push_queue
            SET status = 'pending', error = NULL
            WHERE status = 'failed' AND retry_count < max_retries
        """)
        count = cur.rowcount
        cur.close()
        conn.close()
        log.info(f"Re-queued {count} failed items")
        return

    process_queue(batch_id=args.batch, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd projects/notion && python -m pytest tests/test_push.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add notion-cms/push.py tests/test_push.py
git commit -m "feat(notion-cms): push script — process queue items against Notion API with retry and dry-run"
```

---

## Task 11: End-to-End Smoke Test

**Files:** None new — validates the full pipeline works.

- [ ] **Step 1: Stage a test operation**

Pick one article and stage a harmless property update:

```sql
-- Find a test article
SELECT notion_page_id, title, hub, status
FROM notion_cms.pages
WHERE hub = 'Getting Started' AND type = 'Reference'
LIMIT 1;

-- Stage a no-op property update (set status to its current value)
INSERT INTO notion_cms.push_queue (page_id, operation, payload, batch_id)
SELECT
  notion_page_id,
  'update_properties',
  jsonb_build_object('properties',
    jsonb_build_object('Status', jsonb_build_object('select', jsonb_build_object('name', status)))
  ),
  'smoke-test-001'
FROM notion_cms.pages
WHERE hub = 'Getting Started' AND type = 'Reference'
LIMIT 1;
```

- [ ] **Step 2: Dry run**

```bash
cd projects/notion/notion-cms
python push.py --batch smoke-test-001 --dry-run
```

Expected: `[DRY RUN] #N update_properties: PATCH /pages/{page_id}`

- [ ] **Step 3: Execute for real**

```bash
python push.py --batch smoke-test-001
```

Expected: `#N update_properties: OK`

- [ ] **Step 4: Verify in queue**

```sql
SELECT id, operation, status, pushed_at, error
FROM notion_cms.push_queue WHERE batch_id = 'smoke-test-001';
```

Expected: status = `pushed`, error = NULL.

- [ ] **Step 5: Commit**

```bash
git commit --allow-empty -m "test: end-to-end smoke test passed — push queue → Notion API"
```

---

## Task 12: Full-Text Search Index

**Files:**
- Run SQL migration only

Adds the GIN index for full-text search across all article content.

- [ ] **Step 1: Create the index**

```sql
-- This may already exist from migrate.py, but ensure it's populated:
CREATE INDEX IF NOT EXISTS idx_blocks_search
ON notion_cms.blocks USING gin (to_tsvector('english', COALESCE(rich_text_plain, '')));
```

- [ ] **Step 2: Test a search**

```sql
-- Find all blocks mentioning "fingerprint" across the entire KB
SELECT p.title, p.hub, b.type, b.rich_text_plain
FROM notion_cms.blocks b
JOIN notion_cms.pages p ON b.page_id = p.notion_page_id
WHERE to_tsvector('english', COALESCE(b.rich_text_plain, '')) @@ to_tsquery('fingerprint')
LIMIT 10;
```

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "feat(notion-cms): full-text search index on block content"
```

---

## Execution Summary

| Task | What | Time Estimate |
|------|------|---------------|
| 1 | Schema migration | 5 min |
| 2 | Notion API client | 10 min |
| 3 | Block parser | 10 min |
| 4 | Media handler | 10 min |
| 5 | Pull pages | 5 min code + 4 min run |
| 6 | Pull blocks | 2 min code + 15-20 min run |
| 7 | Pull views & comments | 2 min + 5 min run |
| 8 | Storage setup & image upload | 10 min code + 5 min run |
| 9 | Re-host Notion media | 5 min code + varies |
| 10 | Push script | 15 min |
| 11 | E2E smoke test | 5 min |
| 12 | Full-text search index | 2 min |

**Total:** ~90 min coding + ~30 min pull runtime

## Post-Completion

After all tasks pass, you have a fully operational Notion CMS layer in Supabase:
- `notion_cms.pages` — 715 articles, queryable by hub/section/type/status
- `notion_cms.blocks` — ~37K blocks, searchable, filterable by type/color/media
- `notion_cms.views` — 13 view definitions, pushable back to Notion
- `notion_cms.images` — ~284 branding images in Supabase Storage
- `notion_cms.push_queue` — stage any batch operation, dry-run, push, verify

First batch operations to try:
1. `INSERT INTO push_queue ... SELECT` to add images to all Products articles
2. Restyle all callout blocks to a consistent color
3. Nuke existing views and recreate from Supabase-defined configs

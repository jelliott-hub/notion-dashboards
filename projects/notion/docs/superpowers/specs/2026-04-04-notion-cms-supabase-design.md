# Notion CMS in Supabase — Design Spec

**Date:** 2026-04-04
**Status:** Draft
**Scope:** B4ALL Knowledge Base database (`37ac70bb`) — 715 articles, ~37K blocks, 13 views

## CRITICAL: Target Scope

**There is ONE database. Ignore everything else in the Notion workspace.**

| Field | Value |
|---|---|
| **Database name** | B4ALL Knowledge Base |
| **Database ID** | `37ac70bb-1cc6-4bdc-a52e-f2c8587b636e` |
| **Data Source ID** | `fd44d1a1-ef63-4a64-badb-366b38794cb3` |
| **Database URL** | `https://www.notion.so/37ac70bb1cc64bdca52ef2c8587b636e` |

The workspace has ~90 other data sources — do NOT query, create, modify, or reference any of them. Every operation in this spec targets this single database and its pages.

## Problem

The Notion MCP tools can read pages/properties and manage database schemas, but **cannot** manipulate blocks (the actual content of articles). This means we cannot:

- Batch-add images to articles
- Restyle headings, callouts, or block colors across hundreds of pages
- Inject or restructure block content (add callouts, reorder sections, insert dividers)
- Rebuild views with consistent styling from a central definition
- Do any bulk content operation that requires block-level access

The Notion raw API *can* do all of this, but requires knowing page IDs, block IDs, block structures, and managing rate limits. There is no queryable layer between "I want to change all heading_2 blocks in Products articles" and "send 200 individual PATCH requests."

## Solution

A new `notion_cms` schema on B4All-Hub Supabase that mirrors the KB database's pages, blocks, views, and comments into SQL-queryable tables. Supabase Storage hosts images with permanent public URLs. A push queue stages changes and executes them against the Notion API in controlled batches.

## Workflow

```
1. PULL (one-time)
   Notion API → notion_cms.pages + notion_cms.blocks + notion_cms.views + notion_cms.comments
   Download Notion-hosted media → Supabase Storage (kb-images bucket)
   Upload branding-assets images → Supabase Storage

2. EDIT (iterative, SQL-powered)
   SQL batch operations on blocks/pages/views tables
   Stage changes into notion_cms.push_queue

3. PUSH (batched, rate-limited)
   Process push_queue → Notion API
   3 req/sec, max 100 blocks per append, 2-level nesting limit
   Confirm results, retry failures

4. VERIFY & ITERATE
   Spot-check in Notion, adjust in Supabase, push again
```

Supabase is the workspace. Notion is the render target. No bidirectional sync — edits happen in Supabase, push outward. Bidirectional is a future concern.

## Schema

### `notion_cms.pages`

One row per KB database page (715 articles + hub/section index pages).

```sql
CREATE SCHEMA IF NOT EXISTS notion_cms;

CREATE TABLE notion_cms.pages (
  -- Identity
  notion_page_id       uuid PRIMARY KEY,
  url                  text,
  public_url           text,

  -- Hierarchy
  parent_type          text,                -- 'database_id' | 'page_id' | 'block_id' | 'workspace'
  parent_id            uuid,

  -- Lifecycle
  in_trash             boolean DEFAULT false,
  is_archived          boolean DEFAULT false,
  is_locked            boolean DEFAULT false,

  -- Audit
  created_time         timestamptz,
  created_by           uuid,
  last_edited_time     timestamptz,
  last_edited_by       uuid,

  -- Appearance
  icon                 jsonb,               -- {type: "emoji"|"icon"|"custom_emoji"|"external"|"file"|"file_upload", ...}
  cover                jsonb,               -- {type: "external"|"file"|"file_upload", ...}

  -- KB Properties (denormalized from Notion database properties)
  title                text NOT NULL,
  hub                  text,                -- select: Customer Success, Engineering, Growth, etc.
  section              text,                -- select: 61 options
  sub_section          text,                -- select: 26 options
  type                 text,                -- select: Hub / Section / Reference / SOP / Policy / Guide
  status               text,                -- select: active / current / needs_review / archived
  owner                text,                -- select: operations, customer-success, sales, etc.
  audience             text[],              -- multi_select → postgres array
  topics               text[],              -- multi_select → postgres array
  description          text,
  last_reviewed        date,
  files_and_media      jsonb,               -- file objects array

  -- Relations (as UUID arrays for SQL joins)
  parent_page_ids      uuid[],              -- self-relation "Parent"
  related_page_ids     uuid[],              -- self-relation "Related back to B4ALL Knowledge Base"
  section_page_ids     uuid[],              -- relation to section pages collection

  -- Meta
  block_count          int,
  pulled_at            timestamptz DEFAULT now()
);

CREATE INDEX idx_pages_hub ON notion_cms.pages (hub);
CREATE INDEX idx_pages_section ON notion_cms.pages (section);
CREATE INDEX idx_pages_type ON notion_cms.pages (type);
CREATE INDEX idx_pages_status ON notion_cms.pages (status);
```

### `notion_cms.blocks`

One row per block across all pages (~37,000 rows). Stores the raw Notion block JSON for lossless roundtrip, plus denormalized columns for the fields most useful in batch SQL queries.

```sql
CREATE TABLE notion_cms.blocks (
  -- Identity
  notion_block_id      uuid PRIMARY KEY,
  page_id              uuid NOT NULL REFERENCES notion_cms.pages,
  parent_block_id      uuid,               -- null = top-level block on page

  -- Type & Position
  type                 text NOT NULL,       -- paragraph, heading_1..4, callout, image, tab, code,
                                            -- bulleted_list_item, numbered_list_item, to_do, toggle,
                                            -- quote, divider, table, table_row, column_list, column,
                                            -- bookmark, embed, link_preview, link_to_page, synced_block,
                                            -- equation, breadcrumb, table_of_contents, audio, video,
                                            -- file, pdf, child_page, child_database, template,
                                            -- meeting_notes, unsupported
  sort_order           int NOT NULL,        -- position among siblings
  depth                int DEFAULT 0,       -- nesting level from page root
  has_children         boolean DEFAULT false,

  -- Content (raw Notion JSON — lossless roundtrip)
  content              jsonb NOT NULL,      -- full type-specific object: rich_text array, url, expression, etc.

  -- Denormalized for batch queries
  color                text,                -- 20 values: default, blue, blue_background, brown, brown_background,
                                            -- gray, gray_background, green, green_background, orange,
                                            -- orange_background, pink, pink_background, purple, purple_background,
                                            -- red, red_background, yellow, yellow_background
  rich_text_plain      text,                -- concatenated plain_text for full-text search
  language             text,                -- code blocks only
  is_toggleable        boolean,             -- heading blocks only
  checked              boolean,             -- to_do blocks only
  caption_plain        text,                -- image, video, audio, file, pdf, code, embed blocks

  -- Media (image, video, audio, file, pdf blocks)
  media_type           text,                -- 'external' | 'file' | 'file_upload' (null for non-media)
  media_url            text,                -- original URL (external = permanent, file = 1hr expiry)
  media_expiry         timestamptz,         -- expiry_time for Notion-hosted files
  storage_url          text,                -- Supabase Storage URL after re-hosting

  -- Audit
  created_time         timestamptz,
  created_by           uuid,
  last_edited_time     timestamptz,
  last_edited_by       uuid,
  in_trash             boolean DEFAULT false,

  -- Meta
  pulled_at            timestamptz DEFAULT now()
);

CREATE INDEX idx_blocks_page ON notion_cms.blocks (page_id, sort_order);
CREATE INDEX idx_blocks_type ON notion_cms.blocks (type);
CREATE INDEX idx_blocks_parent ON notion_cms.blocks (parent_block_id);
CREATE INDEX idx_blocks_media ON notion_cms.blocks (page_id) WHERE media_url IS NOT NULL;
CREATE INDEX idx_blocks_search ON notion_cms.blocks USING gin (to_tsvector('english', rich_text_plain));
```

### `notion_cms.views`

One row per database view. Stores the full view configuration as JSONB so views can be defined in Supabase and pushed to Notion.

```sql
CREATE TABLE notion_cms.views (
  -- Identity
  notion_view_id       uuid PRIMARY KEY,
  database_id          uuid NOT NULL,       -- 37ac70bb-1cc6-4bdc-a52e-f2c8587b636e
  data_source_id       text NOT NULL,       -- collection://fd44d1a1-ef63-4a64-badb-366b38794cb3

  -- Definition
  name                 text NOT NULL,
  type                 text NOT NULL,       -- table | board | gallery | list | calendar | timeline
                                            -- | form | chart | map | dashboard
  config               jsonb NOT NULL,      -- full view config: advancedFilter, sorts, groupBy,
                                            -- displayProperties, cover, cardSize, chartConfig,
                                            -- dashboard rows/widgets, etc.

  -- Denormalized for quick lookup
  filter_hub           text,
  filter_type          text,
  group_by_property    text,

  -- Lifecycle
  is_managed           boolean DEFAULT true,-- true = Supabase owns this view definition
  pulled_at            timestamptz DEFAULT now(),
  pushed_at            timestamptz
);
```

### `notion_cms.comments`

Discussion threads on pages and blocks.

```sql
CREATE TABLE notion_cms.comments (
  -- Identity
  notion_comment_id    uuid PRIMARY KEY,
  discussion_id        uuid NOT NULL,       -- groups replies into threads

  -- Location
  parent_type          text NOT NULL,       -- 'page_id' | 'block_id'
  parent_id            uuid NOT NULL,

  -- Content
  rich_text            jsonb NOT NULL,      -- array of rich text objects
  plain_text           text,
  attachments          jsonb,               -- up to 3 file attachments

  -- Audit
  created_time         timestamptz,
  created_by           uuid,
  last_edited_time     timestamptz,
  display_name         jsonb,

  -- Meta
  pulled_at            timestamptz DEFAULT now()
);

CREATE INDEX idx_comments_page ON notion_cms.comments (parent_id);
CREATE INDEX idx_comments_discussion ON notion_cms.comments (discussion_id);
```

### `notion_cms.images`

Registry of images uploaded to Supabase Storage, with optional mapping to target articles.

```sql
CREATE TABLE notion_cms.images (
  id                   bigserial PRIMARY KEY,

  -- Source
  original_filename    text NOT NULL,
  file_hash            text NOT NULL,       -- md5 for dedup
  file_size_bytes      bigint,
  mime_type            text,

  -- Supabase Storage
  storage_path         text NOT NULL UNIQUE,-- kb-images/{hub}/{section}/{filename}
  public_url           text NOT NULL,       -- permanent URL

  -- Mapping
  hub                  text,
  section              text,
  mapped_page_id       uuid REFERENCES notion_cms.pages,
  mapped_block_id      uuid,                -- insert before/after this block (null = append to page)
  category             text,                -- product | screenshot | icon | hero | blog | procedure

  -- Lifecycle
  uploaded_at          timestamptz DEFAULT now(),
  pushed_at            timestamptz
);

CREATE UNIQUE INDEX idx_images_hash ON notion_cms.images (file_hash);
```

### `notion_cms.push_queue`

Staged changes waiting to be pushed to Notion. Decouples "what to change" from "when to push."

```sql
CREATE TABLE notion_cms.push_queue (
  id                   bigserial PRIMARY KEY,

  -- Target
  page_id              uuid REFERENCES notion_cms.pages,
  block_id             uuid,
  view_id              uuid,

  -- Operation
  operation            text NOT NULL,
    -- Page ops:    update_properties, update_icon, update_cover, lock_page, trash_page, archive_page
    -- Block ops:   append_blocks, update_block, delete_block
    -- Media ops:   insert_image, replace_media_url
    -- View ops:    create_view, update_view, delete_view
    -- Comment ops: create_comment
    -- Bulk ops:    replace_page_content (delete all blocks + re-append)
  payload              jsonb NOT NULL,      -- Notion API request body
  position             jsonb,               -- for append: {type: "end"} | {type: "start"} | {type: "after_block", after_block: {id: "..."}}

  -- Execution
  status               text DEFAULT 'pending',  -- pending | queued | pushing | pushed | confirmed | failed
  batch_id             text,                     -- group related ops
  priority             int DEFAULT 0,            -- higher = first within batch
  retry_count          int DEFAULT 0,
  max_retries          int DEFAULT 3,
  error                text,
  error_code           text,                     -- rate_limited, validation_error, etc.

  -- Timing
  created_at           timestamptz DEFAULT now(),
  queued_at            timestamptz,
  pushed_at            timestamptz,
  confirmed_at         timestamptz
);

CREATE INDEX idx_queue_status ON notion_cms.push_queue (status) WHERE status NOT IN ('confirmed', 'failed');
CREATE INDEX idx_queue_batch ON notion_cms.push_queue (batch_id, priority DESC);
CREATE INDEX idx_queue_page ON notion_cms.push_queue (page_id);
```

### `notion_cms.api_constraints`

Reference table encoding Notion API limits. Used by push scripts to self-regulate.

```sql
CREATE TABLE notion_cms.api_constraints (
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
  ('max_filter_nesting',      '2',          'Max compound filter nesting depth');
```

## Supabase Storage

A public bucket `kb-images` on B4All-Hub for hosting article images with permanent URLs.

**Structure:**
```
kb-images/
  branding/                    -- logos, favicons, patterns
  customer-success/            -- support screenshots, procedure images
    applicant-support/
    operator-support/
    ...
  engineering/
    livescan-platform/
    thin-client/
    cms-screenshots/
    ...
  products/
    cardscan/
    livescan/
    ...
  growth/
  implementation/
  tools/
  getting-started/
  templates/
  compliance/
  accounting-finance/
  shared/                      -- images used across multiple hubs
```

**URL pattern:** `https://dozjdswqnzqwvieqvwpe.supabase.co/storage/v1/object/public/kb-images/{path}`

**Population:**
1. Deduplicate the 394 branding-assets images → ~284 unique by md5 hash
2. Categorize by hub/section based on filename semantics
3. Upload to Storage with organized paths
4. Register in `notion_cms.images` table
5. During pull phase: download any Notion-hosted media (expiring URLs) into Storage and register

## Pull Phase

A Python script that runs once to snapshot the entire KB database into Supabase.

**Steps:**
1. Query KB database via Notion API to get all 715 page IDs + properties
2. For each page, fetch block children recursively (handle `has_children` nesting)
3. Insert into `notion_cms.pages` and `notion_cms.blocks`
4. For blocks with Notion-hosted media (`media_type = 'file'`), download the file before the 1-hour URL expires, upload to Supabase Storage, record `storage_url`
5. Fetch all 13 view configurations, insert into `notion_cms.views`
6. Fetch comments on all pages, insert into `notion_cms.comments`

**Rate management:**
- 3 req/sec sustained → ~240 seconds to fetch 715 pages (properties only)
- Block children: 715 pages x avg ~2 pagination calls = ~1,430 requests → ~8 minutes
- Recursive children for nested blocks: estimate 500 additional calls → ~3 minutes
- Total pull time estimate: ~15-20 minutes

**Pagination handling:**
- Notion returns max 100 blocks per request with cursor-based pagination
- Must recurse into blocks where `has_children = true`
- Store `depth` and `parent_block_id` to reconstruct tree structure

## Edit Phase

SQL-powered batch operations on the Supabase tables. Changes are staged into `push_queue` rather than applied to Notion directly.

**Example operations:**

```sql
-- Find all heading_2 blocks in Products hub articles
SELECT b.* FROM notion_cms.blocks b
JOIN notion_cms.pages p ON b.page_id = p.notion_page_id
WHERE p.hub = 'Products' AND b.type = 'heading_2';

-- Stage: add an image block after the first heading in every Products article
INSERT INTO notion_cms.push_queue (page_id, operation, payload, position)
SELECT
  p.notion_page_id,
  'append_blocks',
  jsonb_build_object('children', jsonb_build_array(
    jsonb_build_object(
      'type', 'image',
      'image', jsonb_build_object(
        'type', 'external',
        'external', jsonb_build_object('url', i.public_url)
      )
    )
  )),
  jsonb_build_object('type', 'after_block',
    'after_block', jsonb_build_object('id', first_heading.notion_block_id::text))
FROM notion_cms.pages p
JOIN notion_cms.images i ON i.mapped_page_id = p.notion_page_id
JOIN LATERAL (
  SELECT notion_block_id FROM notion_cms.blocks
  WHERE page_id = p.notion_page_id AND type LIKE 'heading_%'
  ORDER BY sort_order LIMIT 1
) first_heading ON true
WHERE p.hub = 'Products';

-- Stage: change all callout colors to blue_background
INSERT INTO notion_cms.push_queue (page_id, block_id, operation, payload)
SELECT
  page_id,
  notion_block_id,
  'update_block',
  jsonb_build_object('callout', content || jsonb_build_object('color', 'blue_background'))
FROM notion_cms.blocks
WHERE type = 'callout' AND color != 'blue_background';

-- Stage: rebuild a view with new filter
INSERT INTO notion_cms.push_queue (view_id, operation, payload)
VALUES (
  'a9c46ceb-82b0-4d5b-ae73-a12779ba4dc6',
  'update_view',
  '{"name": "Default view", "type": "table", ...}'::jsonb
);

-- Review what's queued before pushing
SELECT operation, count(*), array_agg(DISTINCT hub) AS hubs
FROM notion_cms.push_queue q
JOIN notion_cms.pages p ON q.page_id = p.notion_page_id
WHERE q.status = 'pending'
GROUP BY operation;
```

## Push Phase

A Python script that processes the push queue in controlled batches.

**Execution model:**
1. Select pending items from `push_queue`, optionally filtered by `batch_id` or `page_id`
2. Group by operation type (page ops, block ops, view ops)
3. Execute against Notion API at 3 req/sec with exponential backoff on 429s
4. Update queue status: `pushing` → `pushed` (or `failed` with error)
5. Optionally verify by re-fetching the target and comparing (status → `confirmed`)

**Operation mapping:**

| Queue Operation | Notion API Call |
|---|---|
| `update_properties` | `PATCH /v1/pages/{page_id}` with `properties` |
| `update_icon` | `PATCH /v1/pages/{page_id}` with `icon` |
| `update_cover` | `PATCH /v1/pages/{page_id}` with `cover` |
| `lock_page` | `PATCH /v1/pages/{page_id}` with `is_locked: true` |
| `trash_page` | `PATCH /v1/pages/{page_id}` with `in_trash: true` |
| `archive_page` | `PATCH /v1/pages/{page_id}` with `is_archived: true` |
| `append_blocks` | `PATCH /v1/blocks/{page_id}/children` with `children` + `position` |
| `update_block` | `PATCH /v1/blocks/{block_id}` with type-specific payload |
| `delete_block` | `DELETE /v1/blocks/{block_id}` |
| `insert_image` | `PATCH /v1/blocks/{page_id}/children` with image block + position |
| `replace_media_url` | `PATCH /v1/blocks/{block_id}` swapping `file` → `external` with `storage_url` |
| `replace_page_content` | Delete all blocks via `DELETE /v1/blocks/{id}` per block, then `PATCH /v1/blocks/{page_id}/children` with full block tree |
| `create_view` | `POST /v1/views` |
| `update_view` | `PATCH /v1/views/{view_id}` |
| `delete_view` | `DELETE /v1/views/{view_id}` |
| `create_comment` | `POST /v1/comments` |

**Batch constraints enforced by push script:**
- Max 100 blocks per append request (split larger payloads)
- Max 2 nesting levels per append (flatten deeper trees into sequential appends)
- Max 500 KB payload (split if exceeded)
- Rich text objects capped at 2,000 chars (split longer text)
- Sleep 0.35s between requests (3 req/sec)
- Exponential backoff on HTTP 429 with `Retry-After` header

**Block reordering:** The Notion API has no move/reorder endpoint. To reorder blocks within a page:
1. Read current block order
2. Delete blocks that need to move (`delete_block`)
3. Re-append them in the desired position (`append_blocks` with `position`)
4. This changes block IDs — update `notion_cms.blocks` accordingly

## API Coverage

### Page fields captured

| Notion Field | Supabase Column | Notes |
|---|---|---|
| `id` | `notion_page_id` | UUID primary key |
| `url` | `url` | |
| `public_url` | `public_url` | null unless published |
| `parent.type` | `parent_type` | |
| `parent.{type}` | `parent_id` | |
| `in_trash` | `in_trash` | |
| `is_archived` | `is_archived` | Separate from in_trash |
| `is_locked` | `is_locked` | |
| `created_time` | `created_time` | |
| `created_by.id` | `created_by` | |
| `last_edited_time` | `last_edited_time` | |
| `last_edited_by.id` | `last_edited_by` | |
| `icon` | `icon` | JSONB, 6 subtypes |
| `cover` | `cover` | JSONB |
| `properties.*` | denormalized columns | See pages table |

### Block types supported

All 36 Notion block types stored in `blocks.type`:

**Text:** paragraph, heading_1, heading_2, heading_3, heading_4, bulleted_list_item, numbered_list_item, to_do, toggle, quote, callout, code, equation

**Container:** column_list, column, table, table_row, tab, synced_block

**Media:** image, video, audio, file, pdf, embed, bookmark, link_preview

**Structural:** divider, breadcrumb, table_of_contents

**Special:** child_page, child_database, template (deprecated), meeting_notes (read-only), link_to_page, unsupported

### Block fields captured

| Notion Field | Supabase Column | Notes |
|---|---|---|
| `id` | `notion_block_id` | |
| `type` | `type` | |
| `{type}` object | `content` | Full JSON, lossless |
| `{type}.color` | `color` | Denormalized |
| `{type}.rich_text` → `plain_text` | `rich_text_plain` | Concatenated for search |
| `{type}.language` | `language` | Code blocks |
| `{type}.is_toggleable` | `is_toggleable` | Headings |
| `{type}.checked` | `checked` | To-do blocks |
| `{type}.caption` → `plain_text` | `caption_plain` | Media/code blocks |
| `{type}.{file_type}.url` | `media_url` | Media blocks |
| `{type}.{file_type}.expiry_time` | `media_expiry` | Notion-hosted only |
| `has_children` | `has_children` | |
| `created_time` | `created_time` | |
| `created_by.id` | `created_by` | |
| `last_edited_time` | `last_edited_time` | |
| `last_edited_by.id` | `last_edited_by` | |
| `in_trash` | `in_trash` | |

### View types supported

All 10: table, board, gallery, list, calendar, timeline, form, chart, map, dashboard. Full config stored as JSONB including filters, sorts, groupBy, chart config, dashboard widget layouts, cover settings, and per-property display options.

### Property types supported

All 23 Notion database property types can be read. The KB database currently uses: title, rich_text (text), select, multi_select, date, relation, files. The schema can accommodate additional property types if the KB schema evolves.

### Intentionally excluded

- `place` property: always returns null via API
- `meeting_notes` block creation: read-only block type
- `button` property: UI-only, not exposed via API
- Real-time bidirectional sync: future scope

## Notion API Constraints Reference

| Constraint | Value |
|---|---|
| Rate limit | 3 req/sec average per integration |
| Max blocks per append | 100 |
| Max nesting per append | 2 levels |
| Max payload | 500 KB |
| Max rich_text chars | 2,000 per object |
| Max equation chars | 1,000 |
| File URL expiry | 1 hour (Notion-hosted) |
| Max file size (paid) | 5 GiB |
| Max relations per property | 100 |
| Max multi_select options | 100 |
| Pagination max page_size | 100 |
| Max comment attachments | 3 |
| Max sorts per view | 100 |
| Max filter nesting | 2 levels |

## File Structure

```
projects/notion/
  notion-cms/
    pull.py              -- One-time pull: Notion → Supabase
    push.py              -- Process push_queue → Notion API
    storage.py           -- Upload/manage images in Supabase Storage
    migrate.py           -- Run the schema migration
    utils/
      notion_client.py   -- Rate-limited Notion API wrapper
      block_parser.py    -- Parse blocks into flat rows with denormalized fields
      media_handler.py   -- Download Notion-hosted media, upload to Storage
    requirements.txt
```

## Success Criteria

1. All 715 pages with properties are in `notion_cms.pages`
2. All ~37,000 blocks are in `notion_cms.blocks` with lossless `content` JSON
3. All 13 views are in `notion_cms.views` with full config
4. All Notion-hosted media is re-hosted in Supabase Storage with permanent URLs
5. Branding-assets images are uploaded, deduplicated, and registered in `notion_cms.images`
6. A push queue operation can update a block in Notion and the change is visible
7. A batch operation (e.g., "add image to all Products articles") can be staged in SQL, reviewed, and pushed

## Risks

| Risk | Mitigation |
|---|---|
| Pull takes too long (715 pages x recursive blocks) | Parallelize with async requests within rate limit; estimate ~15-20 min |
| Notion-hosted media URLs expire during pull | Download media immediately after fetching each page's blocks |
| Block reordering requires delete + recreate (changes IDs) | Track old→new ID mapping in push_queue; update blocks table after push |
| Rich text > 2,000 chars per object | Split during push; the pull stores the original segments |
| Future KB schema changes (new properties) | Properties are columns — add a migration when new ones appear |
| Push failures leave partial state | Push queue tracks per-item status; re-run only failed items |

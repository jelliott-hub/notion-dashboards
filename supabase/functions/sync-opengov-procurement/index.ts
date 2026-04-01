import * as postgres from "https://deno.land/x/postgres@v0.19.3/mod.ts";

const databaseUrl = Deno.env.get("SUPABASE_DB_URL");

// --- Config ---
const OPENGOV_SEARCH_URL = "https://procurement.opengov.com/api/opportunities/search";
const PAGE_SIZE = 50;
const MAX_PAGES = 10;

const SEARCH_TERMS = [
  "biometric",
  "fingerprint",
  "livescan",
  "live scan",
  "background check",
  "identity verification",
  "FBI enrollment",
  "CJIS",
  "access control badging",
  "credential verification",
  "vetting services",
];

const HIGH_KEYWORDS = [
  "biometric", "fingerprint", "livescan", "live scan", "identity verif",
  "background check", "fbi", "doj", "enrollment station", "access control",
  "credential", "badging", "vetting", "cjis",
];
const MEDIUM_KEYWORDS = [
  "security", "staffing", "screening", "law enforcement", "corrections",
  "public safety", "police", "detention", "probation",
];

function scoreRelevance(text: string): string {
  const lower = text.toLowerCase();
  for (const kw of HIGH_KEYWORDS) {
    if (lower.includes(kw)) return "HIGH";
  }
  for (const kw of MEDIUM_KEYWORDS) {
    if (lower.includes(kw)) return "MEDIUM";
  }
  return "LOW";
}

interface OpportunityRecord {
  opportunity_id: string;
  issuing_agency: string | null;
  title: string;
  description: string | null;
  posted_date: string | null;
  due_date: string | null;
  status: string | null;
  state: string | null;
  county: string | null;
  city: string | null;
  opportunity_url: string | null;
  relevance: string;
  source_search_term: string;
}

// --- Strategy 1: OpenGov internal search API ---
// OpenGov does NOT have a documented public API. This attempts their internal
// search endpoint used by the frontend. If it returns 403/404/etc, we fall
// back entirely to email parsing (Strategy 2).
async function tryOpenGovApi(searchTerm: string): Promise<OpportunityRecord[]> {
  const results: OpportunityRecord[] = [];
  let page = 1;
  let hasMore = true;

  while (hasMore && page <= MAX_PAGES) {
    try {
      const params = new URLSearchParams({
        q: searchTerm,
        page: String(page),
        per_page: String(PAGE_SIZE),
        status: "open",
      });

      const res = await fetch(`${OPENGOV_SEARCH_URL}?${params}`, {
        method: "GET",
        headers: {
          "Accept": "application/json",
          "User-Agent": "B4All-Hub/1.0 (procurement-monitor)",
        },
      });

      if (!res.ok) {
        console.warn(`OpenGov API returned ${res.status} for "${searchTerm}" page ${page}`);
        return results;
      }

      const data = await res.json();
      const items = data.results || data.opportunities || data.data || [];

      if (!Array.isArray(items) || items.length === 0) {
        hasMore = false;
        break;
      }

      for (const item of items) {
        const title = item.title || item.name || "";
        const desc = item.description || item.summary || "";
        const combinedText = `${title} ${desc}`;

        results.push({
          opportunity_id: String(
            item.id || item.opportunity_id || item.bid_id ||
            `og-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
          ),
          issuing_agency: item.agency_name || item.organization_name || item.issuer || null,
          title: title || "Untitled Opportunity",
          description: desc || null,
          posted_date: item.posted_date || item.published_at || item.created_at || null,
          due_date: item.due_date || item.close_date || item.deadline || null,
          status: item.status || "open",
          state: item.state || item.state_code || null,
          county: item.county || null,
          city: item.city || null,
          opportunity_url: item.url || item.link ||
            (item.id ? `https://procurement.opengov.com/portal/opengov/opportunity/${item.id}` : null),
          relevance: scoreRelevance(combinedText),
          source_search_term: searchTerm,
        });
      }

      hasMore = items.length === PAGE_SIZE;
      page++;
    } catch (err) {
      console.warn(`OpenGov API error for "${searchTerm}": ${err.message}`);
      return results;
    }
  }

  return results;
}

// --- Strategy 2: Parse email notifications from raw_emails ---
// Parses "New Opportunity Issued by <Agency>: <Title>" emails from
// procurement-notifications@opengov.com. This is the reliable fallback
// since the API is undocumented and may block server-side requests.
async function parseEmailNotifications(
  conn: postgres.PoolClient,
  lastSyncDate: string | null,
): Promise<OpportunityRecord[]> {
  const results: OpportunityRecord[] = [];

  // Use parameterized date filter when available
  let query: string;
  let params: unknown[];

  if (lastSyncDate) {
    query = `SELECT message_id, subject, body_text, received_at
     FROM raw_emails.messages
     WHERE from_address = 'procurement-notifications@opengov.com'
       AND subject LIKE 'New Opportunity Issued by %'
       AND received_at >= $1::timestamptz
     ORDER BY received_at DESC`;
    params = [lastSyncDate];
  } else {
    query = `SELECT message_id, subject, body_text, received_at
     FROM raw_emails.messages
     WHERE from_address = 'procurement-notifications@opengov.com'
       AND subject LIKE 'New Opportunity Issued by %'
     ORDER BY received_at DESC`;
    params = [];
  }

  const emailRes = await conn.queryObject<{
    message_id: string;
    subject: string;
    body_text: string;
    received_at: string;
  }>(query, params);

  console.log(`Found ${emailRes.rows.length} OpenGov email notifications to parse`);

  for (const email of emailRes.rows) {
    // Parse "New Opportunity Issued by <Agency>: <Title>"
    const subjectMatch = email.subject.match(/^New Opportunity Issued by ([^:]+):\s*(.+)$/);
    if (!subjectMatch) continue;

    const agency = subjectMatch[1].trim();
    const title = subjectMatch[2].trim();

    // Extract description from body text
    let description: string | null = null;
    const body = email.body_text || "";
    const summaryMatch = body.match(/Here is a summary of the project:\s*(.+?)(?:\n\n|Please click)/s);
    if (summaryMatch) {
      description = summaryMatch[1].trim();
    }

    // Extract state from agency name patterns like "City of Gainesville, FL"
    const stateMatch = agency.match(/,\s*([A-Z]{2})\b/);
    const state = stateMatch ? stateMatch[1] : null;

    // Determine county vs city from agency name
    let county: string | null = null;
    let city: string | null = null;
    if (agency.toLowerCase().includes("county")) {
      county = agency;
    } else if (agency.toLowerCase().includes("city") || agency.toLowerCase().includes("town")) {
      city = agency;
    }

    const combinedText = `${title} ${description || ""} ${agency}`;
    const relevance = scoreRelevance(combinedText);

    // Create a stable opportunity_id from the subject line
    const opportunityId = `og-email-${hashCode(email.subject)}`;

    results.push({
      opportunity_id: opportunityId,
      issuing_agency: agency,
      title,
      description,
      posted_date: email.received_at.substring(0, 10),
      due_date: null, // Not available in email notifications
      status: "open",
      state,
      county,
      city,
      opportunity_url: null, // URL is embedded in HTML, not plain text
      relevance,
      source_search_term: "email_notification",
    });
  }

  return results;
}

// Simple string hash for generating stable IDs
function hashCode(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(36);
}

// --- Main Handler ---
Deno.serve(async (_req: Request) => {
  if (!databaseUrl) {
    return new Response(JSON.stringify({ error: "Missing SUPABASE_DB_URL" }), { status: 500 });
  }

  const pool = new postgres.Pool(databaseUrl, 3, true);
  const conn = await pool.connect();
  const startedAt = new Date().toISOString();
  let logId: number | null = null;

  try {
    // Insert sync_log entry
    const logRes = await conn.queryObject<{ id: number }>(
      `INSERT INTO market.sync_log (source_key, sync_type, started_at, status)
       VALUES ('opengov_procurement', 'incremental', $1, 'running') RETURNING id`,
      [startedAt],
    );
    logId = logRes.rows[0].id;

    // Check last successful sync date for incremental
    const lastSyncRes = await conn.queryObject<{ completed_at: string }>(
      `SELECT completed_at FROM market.sync_log
       WHERE source_key = 'opengov_procurement' AND status = 'success'
       ORDER BY completed_at DESC LIMIT 1`,
    );
    const lastSyncDate = lastSyncRes.rows.length > 0
      ? lastSyncRes.rows[0].completed_at?.substring(0, 10)
      : null;

    console.log(`Last sync date: ${lastSyncDate || "never (full sync)"}`);

    // Collect all opportunities, deduped by opportunity_id
    const opportunityMap = new Map<string, OpportunityRecord>();
    let apiSucceeded = false;

    // -- Strategy 1: Try OpenGov search API --
    console.log("Attempting OpenGov search API...");
    for (const term of SEARCH_TERMS) {
      console.log(`Searching API for "${term}"...`);
      const opps = await tryOpenGovApi(term);
      if (opps.length > 0) {
        apiSucceeded = true;
        for (const o of opps) {
          if (!opportunityMap.has(o.opportunity_id)) {
            opportunityMap.set(o.opportunity_id, o);
          }
        }
      }
    }

    if (!apiSucceeded) {
      console.log("OpenGov API unavailable or returned no results. Falling back to email parsing.");
    }

    // -- Strategy 2: Always parse email notifications (catches what API might miss) --
    console.log("Parsing OpenGov email notifications...");
    const emailOpps = await parseEmailNotifications(conn, apiSucceeded ? lastSyncDate : null);
    for (const o of emailOpps) {
      if (!opportunityMap.has(o.opportunity_id)) {
        opportunityMap.set(o.opportunity_id, o);
      }
    }

    const allOpps = Array.from(opportunityMap.values());
    console.log(`Total unique opportunities: ${allOpps.length} (API: ${apiSucceeded}, emails: ${emailOpps.length})`);

    // Upsert into fact_opengov_opportunity
    let rowsInserted = 0;
    let rowsUpdated = 0;

    for (const o of allOpps) {
      const result = await conn.queryObject(
        `INSERT INTO market.fact_opengov_opportunity (
          opportunity_id, issuing_agency, title, description,
          posted_date, due_date, status, state, county, city,
          opportunity_url, relevance, source_search_term, fetched_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,now())
        ON CONFLICT (opportunity_id) DO UPDATE SET
          issuing_agency = EXCLUDED.issuing_agency,
          title = EXCLUDED.title,
          description = COALESCE(EXCLUDED.description, market.fact_opengov_opportunity.description),
          posted_date = COALESCE(EXCLUDED.posted_date, market.fact_opengov_opportunity.posted_date),
          due_date = COALESCE(EXCLUDED.due_date, market.fact_opengov_opportunity.due_date),
          status = EXCLUDED.status,
          state = COALESCE(EXCLUDED.state, market.fact_opengov_opportunity.state),
          county = COALESCE(EXCLUDED.county, market.fact_opengov_opportunity.county),
          city = COALESCE(EXCLUDED.city, market.fact_opengov_opportunity.city),
          opportunity_url = COALESCE(EXCLUDED.opportunity_url, market.fact_opengov_opportunity.opportunity_url),
          relevance = EXCLUDED.relevance,
          source_search_term = EXCLUDED.source_search_term,
          fetched_at = now()
        RETURNING (xmax = 0) AS is_insert`,
        [
          o.opportunity_id, o.issuing_agency, o.title, o.description,
          o.posted_date, o.due_date, o.status, o.state, o.county, o.city,
          o.opportunity_url, o.relevance, o.source_search_term,
        ],
      );
      const row = result.rows[0] as Record<string, unknown>;
      if (row.is_insert) rowsInserted++;
      else rowsUpdated++;
    }

    // Update sync_log with success
    await conn.queryObject(
      `UPDATE market.sync_log SET
        completed_at = now(), status = 'success',
        rows_fetched = $1, rows_inserted = $2, rows_updated = $3,
        metadata = $4
       WHERE id = $5`,
      [
        allOpps.length, rowsInserted, rowsUpdated,
        JSON.stringify({
          api_succeeded: apiSucceeded,
          search_terms: SEARCH_TERMS.length,
          email_notifications_parsed: emailOpps.length,
          unique_opportunities: allOpps.length,
          last_sync_date: lastSyncDate,
          relevance_breakdown: {
            high: allOpps.filter((o) => o.relevance === "HIGH").length,
            medium: allOpps.filter((o) => o.relevance === "MEDIUM").length,
            low: allOpps.filter((o) => o.relevance === "LOW").length,
          },
        }),
        logId,
      ],
    );

    // Update ref_data_source
    await conn.queryObject(
      `UPDATE market.ref_data_source SET notes = 'Last synced: ' || now()::text WHERE source_key = 'opengov_procurement'`,
    );

    console.log(`Done. Inserted: ${rowsInserted}, Updated: ${rowsUpdated}`);

    return new Response(
      JSON.stringify({
        success: true,
        api_succeeded: apiSucceeded,
        rows_fetched: allOpps.length,
        rows_inserted: rowsInserted,
        rows_updated: rowsUpdated,
        email_notifications_parsed: emailOpps.length,
        relevance: {
          high: allOpps.filter((o) => o.relevance === "HIGH").length,
          medium: allOpps.filter((o) => o.relevance === "MEDIUM").length,
          low: allOpps.filter((o) => o.relevance === "LOW").length,
        },
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  } catch (err) {
    console.error("sync-opengov-procurement error:", err);

    // Log failure
    if (logId) {
      try {
        await conn.queryObject(
          `UPDATE market.sync_log SET completed_at = now(), status = 'error', error_message = $1 WHERE id = $2`,
          [err.message || String(err), logId],
        );
      } catch (_) { /* ignore logging error */ }
    }

    return new Response(
      JSON.stringify({ error: err.message || String(err) }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  } finally {
    conn.release();
  }
});

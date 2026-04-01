import * as postgres from "https://deno.land/x/postgres@v0.19.3/mod.ts";

const databaseUrl = Deno.env.get("SUPABASE_DB_URL");

// --- Config ---
const USASPENDING_BASE = "https://api.usaspending.gov/api/v2";
const PAGE_SIZE = 100;
const MAX_PAGES = 10; // Safety cap: 1000 awards max per search

const NAICS_CODES = ["561611", "561612", "561613", "561621", "541990"];

const KEYWORD_SEARCHES = [
  "biometric",
  "fingerprint",
  "livescan",
  "background check",
  "identity verification",
  "FBI enrollment",
  "CJIS",
  "live scan",
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

function scoreRelevance(description: string | null, naics: string | null): string {
  const text = ((description || "") + " " + (naics || "")).toLowerCase();
  for (const kw of HIGH_KEYWORDS) {
    if (text.includes(kw)) return "HIGH";
  }
  for (const kw of MEDIUM_KEYWORDS) {
    if (text.includes(kw)) return "MEDIUM";
  }
  return "LOW";
}

interface AwardRecord {
  award_id: string;
  recipient_name: string | null;
  recipient_uei: string | null;
  awarding_agency: string | null;
  awarding_sub_agency: string | null;
  award_amount: number | null;
  total_obligation: number | null;
  period_of_performance_start: string | null;
  period_of_performance_end: string | null;
  naics_code: string | null;
  naics_description: string | null;
  description: string | null;
  place_of_performance_state: string | null;
  place_of_performance_city: string | null;
  award_type: string | null;
  solicitation_id: string | null;
  relevance: string;
}

async function fetchAwardsByFilters(
  filters: Record<string, unknown>[],
  lastSyncDate: string | null,
): Promise<AwardRecord[]> {
  const allAwards: AwardRecord[] = [];
  let page = 1;
  let hasMore = true;

  const timeFilter = lastSyncDate
    ? [{ field: "date_signed", operation: "greater_than_or_equal", value: lastSyncDate }]
    : [{ field: "date_signed", operation: "greater_than_or_equal", value: "2020-01-01" }];

  while (hasMore && page <= MAX_PAGES) {
    const body = {
      filters: [...filters, ...timeFilter],
      fields: [
        "Award ID", "Recipient Name", "Recipient UEI", "Awarding Agency",
        "Awarding Sub Agency", "Award Amount", "Total Obligation",
        "Start Date", "End Date", "NAICS Code", "NAICS Description",
        "Description", "Place of Performance State Code",
        "Place of Performance City Code", "Award Type",
        "Contract Award Unique Key",
      ],
      page,
      limit: PAGE_SIZE,
      order: "desc",
      sort: "Award Amount",
      subawards: false,
    };

    const res = await fetch(`${USASPENDING_BASE}/search/spending_by_award/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errText = await res.text();
      console.error(`USASpending API error (page ${page}): ${res.status} ${errText}`);
      break;
    }

    const data = await res.json();
    const results = data.results || [];

    for (const r of results) {
      const desc = r["Description"] || r["description"] || null;
      const naicsDesc = r["NAICS Description"] || r["naics_description"] || null;
      const naicsCode = r["NAICS Code"] || r["naics_code"] || null;

      allAwards.push({
        award_id: r["Award ID"] || r["internal_id"]?.toString() || r["Contract Award Unique Key"] || `unknown-${Date.now()}-${Math.random()}`,
        recipient_name: r["Recipient Name"] || r["recipient_name"] || null,
        recipient_uei: r["Recipient UEI"] || null,
        awarding_agency: r["Awarding Agency"] || r["awarding_agency"] || null,
        awarding_sub_agency: r["Awarding Sub Agency"] || r["awarding_sub_agency"] || null,
        award_amount: r["Award Amount"] != null ? Number(r["Award Amount"]) : null,
        total_obligation: r["Total Obligation"] != null ? Number(r["Total Obligation"]) : null,
        period_of_performance_start: r["Start Date"] || r["start_date"] || null,
        period_of_performance_end: r["End Date"] || r["end_date"] || null,
        naics_code: naicsCode,
        naics_description: naicsDesc,
        description: desc,
        place_of_performance_state: r["Place of Performance State Code"] || null,
        place_of_performance_city: r["Place of Performance City Code"] || null,
        award_type: r["Award Type"] || r["award_type"] || null,
        solicitation_id: null,
        relevance: scoreRelevance(desc, naicsDesc),
      });
    }

    hasMore = results.length === PAGE_SIZE;
    page++;
  }

  return allAwards;
}

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
       VALUES ('usaspending', 'incremental', $1, 'running') RETURNING id`,
      [startedAt],
    );
    logId = logRes.rows[0].id;

    // Check last successful sync date for incremental
    const lastSyncRes = await conn.queryObject<{ completed_at: string }>(
      `SELECT completed_at FROM market.sync_log
       WHERE source_key = 'usaspending' AND status = 'success'
       ORDER BY completed_at DESC LIMIT 1`,
    );
    const lastSyncDate = lastSyncRes.rows.length > 0
      ? lastSyncRes.rows[0].completed_at?.substring(0, 10)
      : null;

    console.log(`Last sync date: ${lastSyncDate || "never (full sync)"}`);

    // Collect all awards from multiple search strategies
    const awardMap = new Map<string, AwardRecord>();

    // Strategy 1: Search by NAICS codes
    for (const naics of NAICS_CODES) {
      console.log(`Fetching NAICS ${naics}...`);
      const filters = [{ field: "naics_codes", operation: "search", value: naics }];
      const awards = await fetchAwardsByFilters(filters, lastSyncDate);
      for (const a of awards) {
        if (!awardMap.has(a.award_id)) awardMap.set(a.award_id, a);
      }
    }

    // Strategy 2: Search by keywords
    for (const kw of KEYWORD_SEARCHES) {
      console.log(`Fetching keyword "${kw}"...`);
      const filters = [{ field: "keyword_search", operation: "search", value: kw }];
      const awards = await fetchAwardsByFilters(filters, lastSyncDate);
      for (const a of awards) {
        if (!awardMap.has(a.award_id)) awardMap.set(a.award_id, a);
      }
    }

    const allAwards = Array.from(awardMap.values());
    console.log(`Total unique awards fetched: ${allAwards.length}`);

    // Upsert into fact_federal_award
    let rowsInserted = 0;
    let rowsUpdated = 0;

    for (const a of allAwards) {
      const result = await conn.queryObject(
        `INSERT INTO market.fact_federal_award (
          award_id, recipient_name, recipient_uei, awarding_agency, awarding_sub_agency,
          award_amount, total_obligation, period_of_performance_start, period_of_performance_end,
          naics_code, naics_description, description, place_of_performance_state,
          place_of_performance_city, award_type, solicitation_id, relevance, fetched_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,now())
        ON CONFLICT (award_id) DO UPDATE SET
          recipient_name = EXCLUDED.recipient_name,
          recipient_uei = EXCLUDED.recipient_uei,
          awarding_agency = EXCLUDED.awarding_agency,
          awarding_sub_agency = EXCLUDED.awarding_sub_agency,
          award_amount = EXCLUDED.award_amount,
          total_obligation = EXCLUDED.total_obligation,
          period_of_performance_start = EXCLUDED.period_of_performance_start,
          period_of_performance_end = EXCLUDED.period_of_performance_end,
          naics_code = EXCLUDED.naics_code,
          naics_description = EXCLUDED.naics_description,
          description = EXCLUDED.description,
          place_of_performance_state = EXCLUDED.place_of_performance_state,
          place_of_performance_city = EXCLUDED.place_of_performance_city,
          award_type = EXCLUDED.award_type,
          solicitation_id = EXCLUDED.solicitation_id,
          relevance = EXCLUDED.relevance,
          fetched_at = now()
        RETURNING (xmax = 0) AS is_insert`,
        [
          a.award_id, a.recipient_name, a.recipient_uei, a.awarding_agency, a.awarding_sub_agency,
          a.award_amount, a.total_obligation, a.period_of_performance_start, a.period_of_performance_end,
          a.naics_code, a.naics_description, a.description, a.place_of_performance_state,
          a.place_of_performance_city, a.award_type, a.solicitation_id, a.relevance,
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
        allAwards.length, rowsInserted, rowsUpdated,
        JSON.stringify({
          naics_searches: NAICS_CODES.length,
          keyword_searches: KEYWORD_SEARCHES.length,
          unique_awards: allAwards.length,
          last_sync_date: lastSyncDate,
          relevance_breakdown: {
            high: allAwards.filter((a) => a.relevance === "HIGH").length,
            medium: allAwards.filter((a) => a.relevance === "MEDIUM").length,
            low: allAwards.filter((a) => a.relevance === "LOW").length,
          },
        }),
        logId,
      ],
    );

    // Update ref_data_source
    await conn.queryObject(
      `UPDATE market.ref_data_source SET notes = 'Last synced: ' || now()::text WHERE source_key = 'usaspending'`,
    );

    console.log(`Done. Inserted: ${rowsInserted}, Updated: ${rowsUpdated}`);

    return new Response(
      JSON.stringify({
        success: true,
        rows_fetched: allAwards.length,
        rows_inserted: rowsInserted,
        rows_updated: rowsUpdated,
        relevance: {
          high: allAwards.filter((a) => a.relevance === "HIGH").length,
          medium: allAwards.filter((a) => a.relevance === "MEDIUM").length,
          low: allAwards.filter((a) => a.relevance === "LOW").length,
        },
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  } catch (err) {
    console.error("sync-usaspending error:", err);

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

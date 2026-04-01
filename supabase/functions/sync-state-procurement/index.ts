import * as postgres from "https://deno.land/x/postgres@v0.19.3/mod.ts";

const databaseUrl = Deno.env.get("SUPABASE_DB_URL");

// --- Relevance scoring ---
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

// --- Junk filter ---
const JUNK_PATTERNS = [
  /vip.*password/i,
  /password.*expire/i,
  /vendor scam alert/i,
  /scam emails/i,
  /\blogin\b/i,
  /user account.*activated/i,
  /login id request/i,
  /automatic reply/i,
  /^re:/i,
];

function isJunk(subject: string): boolean {
  return JUNK_PATTERNS.some((p) => p.test(subject));
}

// --- Parsed record type ---
interface StateOpportunity {
  source_platform: string;
  solicitation_id: string | null;
  title: string | null;
  agency: string | null;
  state: string;
  posted_date: string | null;
  due_date: string | null;
  status: string | null;
  bid_type: string | null;
  description: string | null;
  opportunity_url: string | null;
  alert_type: string;
  relevance: string;
  email_message_id: string;
}

// --- PA eMarketplace parser ---
function parsePA(messageId: string, subject: string, body: string | null, receivedAt: string): StateOpportunity | null {
  // "New Solicitation eAlert for {id} - {title}"
  // "Modified Solicitation eAlert for {id} - {title}"
  // "Cancelled Solicitation eAlert for {id} - {title}"
  let alertType = "other";
  if (subject.includes("New Solicitation")) alertType = "new";
  else if (subject.includes("Modified Solicitation")) alertType = "amended";
  else if (subject.includes("Cancelled Solicitation")) alertType = "cancelled";

  // Extract solicitation_id and title from subject
  const match = subject.match(/eAlert for\s+(\S+)\s*-\s*(.+)$/i);
  const solicitationId = match ? match[1].trim() : null;
  const title = match ? match[2].trim() : subject;

  // Extract agency from body: "{Agency} has posted..."
  let agency: string | null = null;
  if (body && body !== "[deleted from exchange]") {
    const agencyMatch = body.match(/^([A-Z][^\n]{3,80})\s+has posted/m);
    if (agencyMatch) {
      agency = agencyMatch[1].trim();
    }
  }

  // Extract bid_type from subject or solicitation_id patterns
  let bidType: string | null = null;
  const bidTypeMatch = subject.match(/\b(RFP|RFI|IFB|ITB|RFQ|ITN)\b/i);
  if (bidTypeMatch) {
    bidType = bidTypeMatch[1].toUpperCase();
  }

  const combinedText = `${title || ""} ${agency || ""} ${body || ""}`;

  return {
    source_platform: "PA eMarketplace",
    solicitation_id: solicitationId,
    title,
    agency,
    state: "PA",
    posted_date: receivedAt.substring(0, 10),
    due_date: null,
    status: alertType === "cancelled" ? "cancelled" : "open",
    bid_type: bidType,
    description: (body && body !== "[deleted from exchange]") ? body.substring(0, 1000) : null,
    opportunity_url: solicitationId ? `https://www.emarketplace.state.pa.us/Solicitations.aspx?SID=${solicitationId}` : null,
    alert_type: alertType,
    relevance: scoreRelevance(combinedText),
    email_message_id: messageId,
  };
}

// --- FL MFMP parser ---
function parseFL(messageId: string, subject: string, body: string | null, receivedAt: string): StateOpportunity | null {
  // "Advertisement Posted - {type}-{number}"
  // "Advertisement Withdrawn - {type}-{number}"
  let alertType = "other";
  if (subject.includes("Advertisement Posted")) alertType = "new";
  else if (subject.includes("Advertisement Withdrawn")) alertType = "cancelled";

  // Extract solicitation_id from subject
  const solMatch = subject.match(/-\s*([A-Z]+-\d+)\s*$/i);
  const solicitationId = solMatch ? solMatch[1].trim() : null;

  // Extract bid_type from solicitation_id prefix
  let bidType: string | null = null;
  if (solicitationId) {
    const prefix = solicitationId.split("-")[0].toUpperCase();
    if (["RFP", "ITB", "ITN", "SS", "AD", "RFI", "IN"].includes(prefix)) {
      bidType = prefix;
    }
  }

  // Parse body for title, agency, and other details
  let title: string | null = null;
  let agency: string | null = null;
  let description: string | null = null;

  if (body) {
    // Title: "Title: {title}"
    const titleMatch = body.match(/Title:\s*(.+?)(?:\n|Commodity)/s);
    if (titleMatch) title = titleMatch[1].trim();

    // Organization: "Organization: {agency}"
    const orgMatch = body.match(/Organization:\s*(.+?)(?:\n|Advertisement)/s);
    if (orgMatch) agency = orgMatch[1].trim();

    // Advertisement Type for better bid_type
    const advTypeMatch = body.match(/Advertisement Type:\s*(.+?)(?:\n|Title)/s);
    if (advTypeMatch) {
      const advType = advTypeMatch[1].trim();
      if (!bidType || bidType === "AD") {
        if (advType.includes("Request for Proposals")) bidType = "RFP";
        else if (advType.includes("Invitation to Bid")) bidType = "ITB";
        else if (advType.includes("Invitation to Negotiate")) bidType = "ITN";
        else if (advType.includes("Single Source")) bidType = "SS";
      }
    }

    description = body.substring(0, 1000);
  }

  const combinedText = `${title || ""} ${agency || ""} ${description || ""} ${subject}`;

  return {
    source_platform: "FL MFMP",
    solicitation_id: solicitationId,
    title: title || (solicitationId ? `FL ${solicitationId}` : subject),
    agency,
    state: "FL",
    posted_date: receivedAt.substring(0, 10),
    due_date: null,
    status: alertType === "cancelled" ? "cancelled" : "open",
    bid_type: bidType,
    description,
    opportunity_url: solicitationId
      ? `https://vendor.myfloridamarketplace.com/search/bids/detail/${solicitationId}`
      : null,
    alert_type: alertType,
    relevance: scoreRelevance(combinedText),
    email_message_id: messageId,
  };
}

// --- ID LUMA parser ---
function parseID(messageId: string, subject: string, body: string | null, receivedAt: string): StateOpportunity | null {
  // "State of Idaho Bidding Opportunity: {ITB|RFP|RFQ|RFI|BRAND NAME EXEMPTION} {number}"
  // "State of Idaho Bidding Opportunity: ITB 1182 has been amended."
  // "Event: {number} has been amended"
  // "Bidding opportunity: Event #{number} is or will be available for response"
  let alertType = "new";
  if (subject.includes("amended")) alertType = "amended";

  let solicitationId: string | null = null;
  let bidType: string | null = null;
  let title: string | null = null;

  // Pattern 1: "State of Idaho Bidding Opportunity: {type} {number}"
  const lumaMatch = subject.match(/Bidding Opportunity:\s*(ITB|RFP|RFQ|RFI|BRAND NAME EXEMPTION)\s+(\d+)/i);
  if (lumaMatch) {
    bidType = lumaMatch[1].toUpperCase();
    solicitationId = `${bidType} ${lumaMatch[2]}`;
  }

  // Pattern 2: "Event: {number} has been amended" or "Event #{number}"
  if (!solicitationId) {
    const eventMatch = subject.match(/Event[:#]\s*(\d+)/i);
    if (eventMatch) {
      solicitationId = `Event ${eventMatch[1]}`;
    }
  }

  // Parse body for title/agency
  let agency: string | null = null;
  let description: string | null = null;
  if (body && body !== "[deleted from exchange]") {
    // Pattern: "{type} {number} {title} for {AGENCY}"
    const bodyTitleMatch = body.match(/(?:ITB|RFP|RFQ|RFI)\s+\d+\s+(.+?)\s+for\s+([A-Z][A-Z\s]+?)\s+has been/i);
    if (bodyTitleMatch) {
      title = bodyTitleMatch[1].trim();
      agency = bodyTitleMatch[2].trim();
    }
    description = body.substring(0, 1000);
  }

  const combinedText = `${title || ""} ${agency || ""} ${description || ""} ${subject}`;

  return {
    source_platform: "ID LUMA",
    solicitation_id: solicitationId,
    title: title || subject,
    agency,
    state: "ID",
    posted_date: receivedAt.substring(0, 10),
    due_date: null,
    status: "open",
    bid_type: bidType,
    description,
    opportunity_url: null,
    alert_type: alertType,
    relevance: scoreRelevance(combinedText),
    email_message_id: messageId,
  };
}

// --- NV ePro parser ---
function parseNV(messageId: string, subject: string, body: string | null, receivedAt: string): StateOpportunity | null {
  // "Bid Notification - Bid # {id}, {title}"
  // "Bid Amendment Notification - Bid # {id}, {title}"
  // "Bid Awarded - Bid # {id}, {title}"
  // "Quote {id} has been submitted"
  let alertType = "other";
  if (subject.startsWith("Bid Notification")) alertType = "new";
  else if (subject.includes("Bid Amendment")) alertType = "amended";
  else if (subject.includes("Bid Awarded")) alertType = "awarded";
  else if (subject.includes("Quote") && subject.includes("submitted")) alertType = "quote_submitted";

  let solicitationId: string | null = null;
  let title: string | null = null;
  let bidType: string | null = "BID";

  // "Bid # {id}, {title}"
  const bidMatch = subject.match(/Bid #\s*(\S+),\s*(.+)$/i);
  if (bidMatch) {
    solicitationId = bidMatch[1].replace(/,$/, "").trim();
    title = bidMatch[2].trim();
  }

  // Quote pattern
  if (!solicitationId) {
    const quoteMatch = subject.match(/Quote\s+(\S+)\s+has been/i);
    if (quoteMatch) {
      solicitationId = quoteMatch[1].trim();
      bidType = "QUOTE";
    }
  }

  // Extract agency from body: "State of Nevada, {Department}"
  let agency: string | null = null;
  let description: string | null = null;
  if (body) {
    const agencyMatch = body.match(/State of Nevada,\s*(.+?)\./i);
    if (agencyMatch) {
      agency = agencyMatch[1].trim();
    }
    description = body.substring(0, 1000);
  }

  const combinedText = `${title || ""} ${agency || ""} ${description || ""} ${subject}`;

  return {
    source_platform: "NV ePro",
    solicitation_id: solicitationId,
    title: title || subject,
    agency,
    state: "NV",
    posted_date: receivedAt.substring(0, 10),
    due_date: null,
    status: alertType === "awarded" ? "awarded" : "open",
    bid_type: bidType,
    description,
    opportunity_url: solicitationId
      ? `https://nevadaepro.com/bso/view/search/searchBid.xhtml`
      : null,
    alert_type: alertType,
    relevance: scoreRelevance(combinedText),
    email_message_id: messageId,
  };
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
       VALUES ('state_procurement', 'incremental', $1, 'running') RETURNING id`,
      [startedAt],
    );
    logId = logRes.rows[0].id;

    // Check last successful sync date
    const lastSyncRes = await conn.queryObject<{ last_sync: string }>(
      `SELECT to_char(completed_at, 'YYYY-MM-DD') as last_sync
       FROM market.sync_log
       WHERE source_key = 'state_procurement' AND status = 'success'
       ORDER BY completed_at DESC LIMIT 1`,
    );
    const lastSyncDate = lastSyncRes.rows.length > 0
      ? lastSyncRes.rows[0].last_sync
      : null;

    console.log(`Last sync date: ${lastSyncDate || "never (full sync)"}`);

    // Build date filter
    const dateFilter = lastSyncDate
      ? `AND m.received_at >= '${lastSyncDate}'::timestamptz`
      : "";

    // Fetch all relevant emails from the 4 platforms
    const emailQuery = `
      SELECT m.message_id, m.from_address, m.subject, m.body_text, m.received_at::text
      FROM raw_emails.messages m
      WHERE (
        m.from_address ILIKE '%pa.gov%'
        OR m.from_address ILIKE '%myflorida%'
        OR m.from_address ILIKE '%idaho.gov%'
        OR m.from_address ILIKE '%nevadaepro%'
        OR m.from_address ILIKE '%NevadaEPro%'
      )
      AND m.from_address != 'procurement-notifications@opengov.com'
      ${dateFilter}
      ORDER BY m.received_at DESC
    `;

    const emailRes = await conn.queryObject<{
      message_id: string;
      from_address: string;
      subject: string;
      body_text: string | null;
      received_at: string;
    }>(emailQuery);

    console.log(`Found ${emailRes.rows.length} emails to process`);

    const records: StateOpportunity[] = [];
    let skippedJunk = 0;

    for (const email of emailRes.rows) {
      // Skip junk
      if (isJunk(email.subject)) {
        skippedJunk++;
        continue;
      }

      const fromLower = email.from_address.toLowerCase();
      let record: StateOpportunity | null = null;

      if (fromLower.includes("pa.gov")) {
        record = parsePA(email.message_id, email.subject, email.body_text, email.received_at);
      } else if (fromLower.includes("myflorida")) {
        record = parseFL(email.message_id, email.subject, email.body_text, email.received_at);
      } else if (fromLower.includes("idaho.gov")) {
        record = parseID(email.message_id, email.subject, email.body_text, email.received_at);
      } else if (fromLower.includes("nevadaepro")) {
        record = parseNV(email.message_id, email.subject, email.body_text, email.received_at);
      }

      if (record) {
        records.push(record);
      }
    }

    console.log(`Parsed ${records.length} records (skipped ${skippedJunk} junk)`);

    // Upsert into fact_state_opportunity
    let rowsInserted = 0;
    let rowsUpdated = 0;

    for (const r of records) {
      const result = await conn.queryObject(
        `INSERT INTO market.fact_state_opportunity (
          source_platform, solicitation_id, title, agency, state,
          posted_date, due_date, status, bid_type, description,
          opportunity_url, alert_type, relevance, email_message_id, fetched_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,now())
        ON CONFLICT (source_platform, solicitation_id, alert_type, email_message_id)
        DO UPDATE SET
          title = COALESCE(EXCLUDED.title, market.fact_state_opportunity.title),
          agency = COALESCE(EXCLUDED.agency, market.fact_state_opportunity.agency),
          posted_date = COALESCE(EXCLUDED.posted_date, market.fact_state_opportunity.posted_date),
          due_date = COALESCE(EXCLUDED.due_date, market.fact_state_opportunity.due_date),
          status = EXCLUDED.status,
          bid_type = COALESCE(EXCLUDED.bid_type, market.fact_state_opportunity.bid_type),
          description = COALESCE(EXCLUDED.description, market.fact_state_opportunity.description),
          opportunity_url = COALESCE(EXCLUDED.opportunity_url, market.fact_state_opportunity.opportunity_url),
          relevance = EXCLUDED.relevance,
          fetched_at = now()
        RETURNING (xmax = 0) AS is_insert`,
        [
          r.source_platform, r.solicitation_id, r.title, r.agency, r.state,
          r.posted_date, r.due_date, r.status, r.bid_type, r.description,
          r.opportunity_url, r.alert_type, r.relevance, r.email_message_id,
        ],
      );
      const row = result.rows[0] as Record<string, unknown>;
      if (row.is_insert) rowsInserted++;
      else rowsUpdated++;
    }

    // Update sync_log with success
    const relevanceBreakdown = {
      high: records.filter((r) => r.relevance === "HIGH").length,
      medium: records.filter((r) => r.relevance === "MEDIUM").length,
      low: records.filter((r) => r.relevance === "LOW").length,
    };

    const platformBreakdown = {
      pa: records.filter((r) => r.state === "PA").length,
      fl: records.filter((r) => r.state === "FL").length,
      id: records.filter((r) => r.state === "ID").length,
      nv: records.filter((r) => r.state === "NV").length,
    };

    await conn.queryObject(
      `UPDATE market.sync_log SET
        completed_at = now(), status = 'success',
        rows_fetched = $1, rows_inserted = $2, rows_updated = $3,
        metadata = $4
       WHERE id = $5`,
      [
        records.length, rowsInserted, rowsUpdated,
        JSON.stringify({
          emails_scanned: emailRes.rows.length,
          skipped_junk: skippedJunk,
          parsed_records: records.length,
          last_sync_date: lastSyncDate,
          platforms: platformBreakdown,
          relevance: relevanceBreakdown,
        }),
        logId,
      ],
    );

    console.log(`Done. Inserted: ${rowsInserted}, Updated: ${rowsUpdated}`);

    return new Response(
      JSON.stringify({
        success: true,
        emails_scanned: emailRes.rows.length,
        skipped_junk: skippedJunk,
        rows_fetched: records.length,
        rows_inserted: rowsInserted,
        rows_updated: rowsUpdated,
        platforms: platformBreakdown,
        relevance: relevanceBreakdown,
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  } catch (err) {
    console.error("sync-state-procurement error:", err);

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

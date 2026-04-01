import * as postgres from "https://deno.land/x/postgres@v0.19.3/mod.ts";

const notionToken = Deno.env.get("NOTION_API_KEY");
const databaseUrl = Deno.env.get("SUPABASE_DB_URL");

const BLOCK_DAILY = "33513d36-77c3-8109-844b-cb7924718bfd";
const BLOCK_DEFLECTION = "33513d36-77c3-81ff-b320-ca4550d7251b";
const BLOCK_QUEUE = "33513d36-77c3-8160-8e66-ed7b50f4e070";
const BLOCK_OUTCOMES = "33513d36-77c3-814d-aeeb-f9e2846499ef";

// Reusable Notion Updater
async function updateNotionMermaid(blockId: string, mermaidCode: string) {
  const res = await fetch(`https://api.notion.com/v1/blocks/${blockId}`, {
    method: "PATCH",
    headers: {
      "Authorization": `Bearer ${notionToken}`,
      "Content-Type": "application/json",
      "Notion-Version": "2022-06-28"
    },
    body: JSON.stringify({
      code: {
        language: "mermaid",
        rich_text: [{ text: { content: mermaidCode } }]
      }
    })
  });
  if (!res.ok) throw new Error(`Notion error: ${await res.text()}`);
}

Deno.serve(async (req) => {
  if (!notionToken || !databaseUrl) {
    return new Response(JSON.stringify({ error: "Missing environment credentials" }), { status: 500 });
  }

  // Uses connection pooling automatically in Supabase
  const pool = new postgres.Pool(databaseUrl, 3, true);
  const conn = await pool.connect();

  try {
    console.log("Fetching Chart 1: Daily Volume...");
    const res1 = await conn.queryObject(`
        WITH interaction_starts AS (
            SELECT 
                call_key,
                start_time,
                caller_phone,
                LAG(start_time) OVER (PARTITION BY caller_phone ORDER BY start_time) as prev_start_time
            FROM analytics.fact_calls
            WHERE start_time >= '2026-03-01'
        ),
        valid_interactions AS (
            SELECT start_time 
            FROM interaction_starts 
            WHERE prev_start_time IS NULL OR EXTRACT(EPOCH FROM (start_time - prev_start_time)) > 3600
        )
        SELECT to_char(DATE_TRUNC('day', start_time), 'MM-DD') as day, count(*) as c
        FROM valid_interactions
        GROUP BY day ORDER BY day;
    `);
    const dailyData = res1.rows as any[];
    const daysX = dailyData.map(d => d.day);
    const daysY = dailyData.map(d => Number(d.c));

    const chart1 = `xychart-beta
    title "Total Daily Interactions (Dialpad + Bland)"
    x-axis [${daysX.map((d: any) => `"${String(d).trim()}"`).join(', ')}]
    y-axis "Deduped Calls" 0 --> ${Math.max(...daysY) + 50}
    bar [${daysY.join(', ')}]`;
    
    await updateNotionMermaid(BLOCK_DAILY, chart1);

    console.log("Chart 1 Updated. Remaining queries run automatically via pg_cron in full deployment.");

    return new Response(JSON.stringify({ success: true, message: "Sync successful." }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    console.error(err);
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  } finally {
    conn.release();
  }
});

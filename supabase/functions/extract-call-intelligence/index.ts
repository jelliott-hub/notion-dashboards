// supabase/functions/extract-call-intelligence/index.ts
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import * as postgres from "https://deno.land/x/postgres@v0.19.3/mod.ts";
import { preFilter } from "./lib/pre-filter.ts";
import { buildSystemPrompt, buildUserMessage } from "./lib/prompts.ts";
import { dialpadQuery, gotoQuery, blandQuery } from "./lib/input-assembler.ts";
import { resolveEntities } from "./lib/post-process.ts";
import type { CallRecord, ExtractionOutput } from "./lib/types.ts";

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const MODEL = "claude-sonnet-4-20250514";
const MAX_TOKENS = 2000;

Deno.serve(async (req: Request) => {
  const pool = new postgres.Pool(Deno.env.get("SUPABASE_DB_URL")!, 3, true);
  const conn = await pool.connect();

  try {
    // Parse parameters
    const params = await req.json().catch(() => ({}));
    const sourceSystem: string | null = params.source_system || null;
    const batchSize: number = Math.min(params.batch_size || 50, 50);
    const backfill: boolean = params.backfill || false;

    const apiKey = Deno.env.get("ANTHROPIC_API_KEY");
    if (!apiKey) throw new Error("ANTHROPIC_API_KEY not set");

    // Determine which sources to process
    const sources = sourceSystem ? [sourceSystem] : ["dialpad", "goto", "bland"];
    let totalProcessed = 0;
    let totalSkipped = 0;
    let totalErrors = 0;
    let totalInputTokens = 0;
    let totalOutputTokens = 0;

    for (const source of sources) {
      // Get watermark
      const wmResult = await conn.queryObject<{ last_processed_timestamp: string | null }>(
        `SELECT last_processed_timestamp FROM intelligence.call_extraction_state WHERE source_system = $1`,
        [source]
      );
      const since = backfill ? null : wmResult.rows[0]?.last_processed_timestamp || null;

      // Fetch calls
      let query: string;
      switch (source) {
        case "dialpad": query = dialpadQuery(since, batchSize); break;
        case "goto": query = gotoQuery(since, batchSize); break;
        case "bland": query = blandQuery(since, batchSize); break;
        default: continue;
      }

      const callsResult = await conn.queryObject<CallRecord>(query);
      const calls = callsResult.rows;
      if (calls.length === 0) continue;

      let latestTimestamp: string | null = null;
      let sourceProcessed = 0;
      let sourceSkipped = 0;

      for (const call of calls) {
        try {
          // Track latest timestamp for watermark
          if (call.source_timestamp && (!latestTimestamp || call.source_timestamp > latestTimestamp)) {
            latestTimestamp = call.source_timestamp;
          }

          // Pre-filter
          const filterResult = preFilter(call);

          if (!filterResult.pass) {
            // Insert minimal skipped row
            await conn.queryObject(
              `INSERT INTO intelligence.call_intelligence
                (call_key, source_type, source_system, source_id, source_timestamp,
                 direction, duration_seconds, agent_name, caller_name, caller_phone,
                 text_content, has_transcript, skipped_reason, vendor_metadata, classified_at)
               VALUES ($1, 'call', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, now())
               ON CONFLICT (call_key) DO NOTHING`,
              [
                call.call_key, call.source_system, call.source_id, call.source_timestamp,
                call.direction, call.duration_seconds, call.agent_name, call.caller_name,
                call.caller_phone, call.text_content, call.has_transcript,
                filterResult.skipped_reason, JSON.stringify(call.vendor_metadata),
              ]
            );
            sourceSkipped++;
            totalSkipped++;
            continue;
          }

          // Build prompt and call Claude API
          const systemPrompt = buildSystemPrompt(call.source_system);
          const userMessage = buildUserMessage(call);

          const response = await fetch(ANTHROPIC_API_URL, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "x-api-key": apiKey,
              "anthropic-version": "2023-06-01",
            },
            body: JSON.stringify({
              model: MODEL,
              max_tokens: MAX_TOKENS,
              system: systemPrompt,
              messages: [{ role: "user", content: userMessage }],
            }),
          });

          if (response.status === 429) {
            // Rate limited — back off and skip (will be picked up in next batch)
            const retryAfter = parseInt(response.headers.get("retry-after") || "5");
            await new Promise((r) => setTimeout(r, retryAfter * 1000));
            totalErrors++;
            continue;
          }

          if (!response.ok) {
            const errText = await response.text();
            console.error(`Claude API error for ${call.call_key}: ${response.status} ${errText}`);
            totalErrors++;
            continue;
          }

          const apiResult = await response.json();
          const inputTokens: number = apiResult.usage?.input_tokens || 0;
          const outputTokens: number = apiResult.usage?.output_tokens || 0;
          totalInputTokens += inputTokens;
          totalOutputTokens += outputTokens;

          // Parse extraction output
          const rawText: string = apiResult.content?.[0]?.text || "{}";
          let extraction: ExtractionOutput;
          try {
            extraction = JSON.parse(rawText);
          } catch {
            // JSON parse failure — store raw response with confidence=0
            await conn.queryObject(
              `INSERT INTO intelligence.call_intelligence
                (call_key, source_type, source_system, source_id, source_timestamp,
                 direction, duration_seconds, agent_name, caller_name, caller_phone,
                 text_content, has_transcript, vendor_metadata,
                 classification_confidence, raw_response, model, input_tokens, output_tokens, classified_at)
               VALUES ($1, 'call', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 0, $13, $14, $15, $16, now())
               ON CONFLICT (call_key) DO NOTHING`,
              [
                call.call_key, call.source_system, call.source_id, call.source_timestamp,
                call.direction, call.duration_seconds, call.agent_name, call.caller_name,
                call.caller_phone, call.text_content, call.has_transcript,
                JSON.stringify(call.vendor_metadata), JSON.stringify({ raw: rawText }),
                MODEL, inputTokens, outputTokens,
              ]
            );
            totalErrors++;
            continue;
          }

          // Post-process: resolve entities via lookup.find_customer()
          const { entities, matchedClientIds } = await resolveEntities(conn, extraction);

          // Upsert full extracted row
          await conn.queryObject(
            `INSERT INTO intelligence.call_intelligence (
              call_key, source_type, source_system, source_id, source_timestamp,
              direction, duration_seconds, agent_name, caller_name, caller_phone,
              text_content, has_transcript, matched_client_ids, vendor_metadata,
              caller_persona, call_type, call_intent, resolution_status, value_type,
              specificity, summary, relationship_summary, caller_persona_reasoning,
              about_entities, extracted_facts, signal_types, participants,
              unresolved_questions, discrepancies, classification_confidence,
              model, input_tokens, output_tokens, raw_response, classified_at
            ) VALUES (
              $1, 'call', $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
              $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29,
              $30, $31, $32, $33, now()
            ) ON CONFLICT (call_key) DO UPDATE SET
              caller_persona = EXCLUDED.caller_persona,
              call_type = EXCLUDED.call_type,
              call_intent = EXCLUDED.call_intent,
              resolution_status = EXCLUDED.resolution_status,
              value_type = EXCLUDED.value_type,
              specificity = EXCLUDED.specificity,
              summary = EXCLUDED.summary,
              relationship_summary = EXCLUDED.relationship_summary,
              caller_persona_reasoning = EXCLUDED.caller_persona_reasoning,
              about_entities = EXCLUDED.about_entities,
              extracted_facts = EXCLUDED.extracted_facts,
              signal_types = EXCLUDED.signal_types,
              participants = EXCLUDED.participants,
              unresolved_questions = EXCLUDED.unresolved_questions,
              discrepancies = EXCLUDED.discrepancies,
              classification_confidence = EXCLUDED.classification_confidence,
              matched_client_ids = EXCLUDED.matched_client_ids,
              model = EXCLUDED.model,
              input_tokens = EXCLUDED.input_tokens,
              output_tokens = EXCLUDED.output_tokens,
              raw_response = EXCLUDED.raw_response,
              classified_at = now()`,
            [
              call.call_key, call.source_system, call.source_id, call.source_timestamp,
              call.direction, call.duration_seconds, call.agent_name, call.caller_name,
              call.caller_phone, call.text_content, call.has_transcript,
              matchedClientIds, JSON.stringify(call.vendor_metadata),
              extraction.caller_persona, extraction.call_type, extraction.call_intent,
              extraction.resolution_status, extraction.value_type, extraction.specificity,
              extraction.summary, extraction.relationship_summary,
              extraction.caller_persona_reasoning,
              JSON.stringify(entities), JSON.stringify(extraction.extracted_facts),
              extraction.signal_types, JSON.stringify(extraction.participants),
              JSON.stringify(extraction.unresolved_questions),
              JSON.stringify(extraction.discrepancies),
              extraction.classification_confidence,
              MODEL, inputTokens, outputTokens, JSON.stringify(apiResult),
            ]
          );

          sourceProcessed++;
          totalProcessed++;
        } catch (err) {
          console.error(`Error processing ${call.call_key}: ${(err as Error).message}`);
          totalErrors++;
        }
      }

      // Update watermark
      if (latestTimestamp) {
        await conn.queryObject(
          `UPDATE intelligence.call_extraction_state
           SET last_processed_timestamp = $1, last_run_at = now(),
               calls_processed = calls_processed + $2, calls_skipped = calls_skipped + $3
           WHERE source_system = $4`,
          [latestTimestamp, sourceProcessed, sourceSkipped, source]
        );
      }
    }

    // Log to meta.agent_log (non-blocking — schema may vary)
    try {
      await conn.queryObject(
        `INSERT INTO meta.agent_log (agent_name, action, details, created_at)
         VALUES ('extract-call-intelligence', 'batch_run', $1, now())`,
        [JSON.stringify({
          sources,
          processed: totalProcessed,
          skipped: totalSkipped,
          errors: totalErrors,
          input_tokens: totalInputTokens,
          output_tokens: totalOutputTokens,
          backfill,
        })]
      );
    } catch {
      // meta.agent_log may have different schema — non-blocking
    }

    return new Response(
      JSON.stringify({
        processed: totalProcessed,
        skipped: totalSkipped,
        errors: totalErrors,
        input_tokens: totalInputTokens,
        output_tokens: totalOutputTokens,
      }),
      { headers: { "Content-Type": "application/json" } }
    );

  } catch (err) {
    console.error(`Fatal error: ${(err as Error).message}`);
    return new Response(
      JSON.stringify({ error: (err as Error).message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  } finally {
    conn.release();
  }
});

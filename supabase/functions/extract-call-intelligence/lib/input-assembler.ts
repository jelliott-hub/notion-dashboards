// supabase/functions/extract-call-intelligence/lib/input-assembler.ts

/** Fetch Dialpad calls that need processing */
export function dialpadQuery(since: string | null, limit: number): string {
  const whereClause = since
    ? `AND c.date_started > '${since}'::timestamptz`
    : "";

  return `
    SELECT
      'dialpad:' || c.call_id::text AS call_key,
      'dialpad' AS source_system,
      c.call_id::text AS source_id,
      c.date_started AS source_timestamp,
      c.direction,
      (c.duration_ms / 1000)::integer AS duration_seconds,
      c.target_name AS agent_name,
      c.contact_name AS caller_name,
      coalesce(c.contact_phone, c.external_number) AS caller_phone,
      c.ai_recap,
      c.recap_outcome,
      c.recap_purposes,
      c.call_dispositions,
      c.voicemail_link,
      coalesce(t.transcript_text, c.transcript) AS transcript_text,
      t.word_count,
      CASE WHEN coalesce(t.transcript_text, c.transcript) IS NOT NULL THEN true ELSE false END AS has_transcript,
      coalesce(t.transcript_text, c.transcript, c.ai_recap) AS text_content,
      jsonb_build_object(
        'recap_outcome', c.recap_outcome,
        'recap_purposes', c.recap_purposes,
        'call_dispositions', c.call_dispositions,
        'voicemail_link', c.voicemail_link
      ) AS vendor_metadata
    FROM raw_calls.calls_raw_dialpad c
    LEFT JOIN raw_calls.call_transcripts t
      ON t.source_call_id = c.call_id::text AND t.source_system = 'dialpad'
    WHERE NOT EXISTS (
      SELECT 1 FROM intelligence.call_intelligence ci
      WHERE ci.call_key = 'dialpad:' || c.call_id::text
    )
    ${whereClause}
    ORDER BY c.date_started ASC
    LIMIT ${limit};
  `;
}

/** Fetch GoTo calls that need processing */
export function gotoQuery(since: string | null, limit: number): string {
  const whereClause = since
    ? `AND c.start_time > '${since}'::timestamptz`
    : "";

  return `
    SELECT
      'goto:' || c.leg_id AS call_key,
      'goto' AS source_system,
      c.leg_id AS source_id,
      c.start_time AS source_timestamp,
      c.direction,
      c.talk_duration_s::integer AS duration_seconds,
      c.agent_name,
      c.caller_name,
      c.caller_number AS caller_phone,
      t.ai_summary,
      coalesce(t.transcript_text, c.transcript_text) AS transcript_text,
      t.word_count,
      CASE WHEN coalesce(t.transcript_text, c.transcript_text) IS NOT NULL THEN true ELSE false END AS has_transcript,
      coalesce(t.transcript_text, c.transcript_text, t.ai_summary) AS text_content,
      c.outcome,
      jsonb_build_object(
        'outcome', c.outcome,
        'ai_sentiment', c.ai_sentiment,
        'topics', c.topics,
        'disposition', c.disposition
      ) AS vendor_metadata
    FROM raw_calls.calls_raw_goto c
    LEFT JOIN raw_calls.call_transcripts t
      ON t.source_call_id = c.leg_id AND t.source_system = 'goto'
    WHERE NOT EXISTS (
      SELECT 1 FROM intelligence.call_intelligence ci
      WHERE ci.call_key = 'goto:' || c.leg_id
    )
    ${whereClause}
    ORDER BY c.start_time ASC
    LIMIT ${limit};
  `;
}

/** Fetch Bland calls that need processing */
export function blandQuery(since: string | null, limit: number): string {
  const whereClause = since
    ? `AND c.created_at > '${since}'::timestamptz`
    : "";

  return `
    SELECT
      'bland:' || c.call_id AS call_key,
      'bland' AS source_system,
      c.call_id AS source_id,
      c.created_at AS source_timestamp,
      CASE WHEN c.inbound THEN 'inbound' ELSE 'outbound' END AS direction,
      (c.call_length * 60)::integer AS duration_seconds,
      'AI Alex' AS agent_name,
      c.from_number AS caller_name,
      c.from_number AS caller_phone,
      c.summary AS bland_summary,
      c.concatenated_transcript AS transcript_text,
      c.transferred_to AS transfer_target,
      c.call_ended_by,
      c.status,
      c.completed,
      b.persona AS bland_persona,
      b.topic_label,
      b.escalated,
      b.call_quality,
      b.caller_city,
      b.caller_state,
      CASE WHEN c.concatenated_transcript IS NOT NULL THEN true ELSE false END AS has_transcript,
      coalesce(c.concatenated_transcript, c.summary) AS text_content,
      jsonb_build_object(
        'persona', b.persona,
        'topic_label', b.topic_label,
        'topic_node', b.topic_node,
        'escalated', b.escalated,
        'transfer_target', b.transfer_target,
        'call_quality', b.call_quality,
        'reached_wrapup', b.reached_wrapup,
        'caller_city', b.caller_city,
        'caller_state', b.caller_state,
        'status', c.status,
        'completed', c.completed,
        'call_ended_by', c.call_ended_by
      ) AS vendor_metadata
    FROM raw_calls.calls_raw_bland c
    LEFT JOIN raw_calls.bland_call_analysis b ON b.call_id = c.call_id
    WHERE NOT EXISTS (
      SELECT 1 FROM intelligence.call_intelligence ci
      WHERE ci.call_key = 'bland:' || c.call_id
    )
    ${whereClause}
    ORDER BY c.created_at ASC
    LIMIT ${limit};
  `;
}

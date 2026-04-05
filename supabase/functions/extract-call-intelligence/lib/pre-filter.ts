// supabase/functions/extract-call-intelligence/lib/pre-filter.ts
import type { CallRecord, FilterResult } from "./types.ts";

export function preFilter(call: CallRecord): FilterResult {
  switch (call.source_system) {
    case "dialpad":
      return filterDialpad(call);
    case "goto":
      return filterGoto(call);
    case "bland":
      return filterBland(call);
    default:
      return { pass: false, skipped_reason: "unknown_source" };
  }
}

function filterDialpad(call: CallRecord): FilterResult {
  // Check for voicemail (vendor_metadata.voicemail_link)
  if (call.vendor_metadata?.voicemail_link) {
    return { pass: false, skipped_reason: "voicemail" };
  }

  // Duration < 2 minutes
  if (call.duration_seconds < 120) {
    return { pass: false, skipped_reason: "too_short" };
  }

  // Must have recap or transcript
  if (!call.ai_recap && !call.transcript_text && !call.text_content) {
    return { pass: false, skipped_reason: "no_content" };
  }

  return { pass: true };
}

function filterGoto(call: CallRecord): FilterResult {
  // Must be handled
  if (call.vendor_metadata?.outcome !== "handled") {
    return { pass: false, skipped_reason: "not_handled" };
  }

  // Talk duration < 2 minutes
  if (call.duration_seconds < 120) {
    return { pass: false, skipped_reason: "too_short" };
  }

  // Must have summary or transcript
  if (!call.ai_summary && !call.transcript_text && !call.text_content) {
    return { pass: false, skipped_reason: "no_content" };
  }

  return { pass: true };
}

function filterBland(call: CallRecord): FilterResult {
  const transcript = call.transcript_text || call.text_content || "";

  // No content
  if (transcript.trim().length < 50) {
    return { pass: false, skipped_reason: "no_content" };
  }

  // Hangup
  if (call.call_quality === "hangup") {
    return { pass: false, skipped_reason: "hangup" };
  }

  // Zombie records
  if (call.vendor_metadata?.status === "in-progress" || call.vendor_metadata?.completed === false) {
    return { pass: false, skipped_reason: "zombie" };
  }

  // Stuck transfer: transferred + >15 min (duration_seconds > 900)
  if (call.transfer_target && call.duration_seconds > 900) {
    return { pass: false, skipped_reason: "stuck_transfer" };
  }

  // Looping detection: "are you still there" > 3 times
  const loopPhrase = "are you still there";
  const loopCount = (transcript.toLowerCase().split(loopPhrase).length - 1);
  if (loopCount > 3) {
    return { pass: false, skipped_reason: "looping" };
  }

  // Non-transferred Bland calls: skip (soft filter)
  if (!call.transfer_target) {
    return { pass: false, skipped_reason: "non_transferred_bland" };
  }

  return { pass: true };
}

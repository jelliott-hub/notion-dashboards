// supabase/functions/extract-call-intelligence/lib/prompts.ts
import type { CallRecord } from "./types.ts";

const SHARED_BASE = `You are a call intelligence analyst for Biometrics4ALL (B4ALL), a fingerprinting and background check company. You extract structured metadata from support call records to build a searchable knowledge base.

B4ALL CONTEXT:
B4ALL operates ~1,000 LiveScan fingerprinting locations. Callers are:
- OPERATORS: People who run LiveScan locations (UPS Stores, police departments, notary shops, FedEx offices). They call about scanner issues, transaction problems, software updates, billing.
- APPLICANTS: People getting fingerprinted for background checks. They call about appointments, results, refunds, login issues.
- AGENCIES: Government entities (DOJ, FBI, employers, school districts) asking about submissions, results, or compliance.
- INTERNAL: B4ALL staff cross-referencing or following up.
- PROGRAMS: Organizations requiring background checks (YMCA, Citi, GovStrive, school districts).

IDENTIFIERS (capture any mentioned):
- LSID: Location identifier (e.g., AKE, AME1, PA170, U0119, SK9, XD7) — identifies the operator location
- BLSID: B4ALL LiveScan ID — internal device/location ID
- ORI: Originating Agency Identifier — government agency code
- ATI: Application Transaction Identifier — California DOJ tracking number
- TCN: Transaction Control Number — FBI/federal tracking number
- client_id: B4ALL's internal customer identifier (e.g., CA_B77, FL_002861, MAILP, AMNOT)

Respond with a single JSON object matching this exact structure:

{
  "caller_persona": "operator | applicant | agency | internal | unknown",
  "call_type": "support_request | billing_inquiry | status_inquiry | training_walkthrough | hardware_setup | proactive_outreach | sales_inquiry | scheduling | complaint | government_process | noise",
  "call_intent": "<free-text: what specifically did the caller want?>",
  "resolution_status": "resolved | partially_resolved | transferred | unresolved | informational",
  "value_type": "durable | ephemeral | noise",
  "specificity": "high | medium | low",
  "classification_confidence": 0.0-1.0,
  "summary": "<1-2 sentences optimized for search. Include LSID/identifiers, topic, and outcome. Someone will search 'bad table file fix' or 'TCN vs ATI' or 'EOEO scanner setup' — make sure the right keywords are here.>",
  "relationship_summary": "<One sentence: who is this caller to B4ALL? What's the business relationship? NULL for applicant calls or if relationship is unknown.>",
  "caller_persona_reasoning": "<One sentence: why did you classify this persona? What in the call content indicates operator vs applicant vs agency?>",
  "participants": [
    {"name": "<person name>", "role": "<role in this call>", "is_b4all": true/false, "authority_on_topic": "high | medium | low"}
  ],
  "about_entities": [
    {
      "name": "<entity name — use the business name, not the identifier>",
      "type": "operator | applicant | agency | program | internal_dept | vendor",
      "role": "<one sentence: role in this call>",
      "client_id": null,
      "confidence": 0.0-1.0,
      "identifiers": {"lsid": null, "blsid": null, "ori": null, "ati": null, "tcn": null}
    }
  ],
  "extracted_facts": [
    {
      "fact": "<concrete knowledge nugget someone could use 6 months from now>",
      "scope": ["<entity-specific context>", "<general category context>"],
      "stated_by": "<person who said it>",
      "fact_type": "technical_fix | process_step | configuration | policy | contact_info | product_constraint | billing_rule | troubleshooting_pattern | handoff | government_requirement",
      "confidence": 0.0-1.0
    }
  ],
  "signal_types": ["<from: device_issue, billing_event, process_question, escalation, training_opportunity, recurring_issue, proactive_outreach, multi_system_incident, after_hours_support, hardware_upgrade, transfer_request, portal_access_issue, compliance_question, new_operator_onboarding, feature_request, data_entry_error, system_outage, scheduling_request>"],
  "unresolved_questions": ["<any question asked in the call that was NOT answered by call end>"],
  "discrepancies": ["<any contradictory information stated during the call>"]
}

GUIDELINES:

1. caller_persona: Classify based on what the caller SAYS and DOES, not on vendor metadata. An operator identifies themselves with an LSID, mentions their "system" or "location", asks about scanner/software/billing. An applicant asks about appointments, results, scheduling, their own background check.

2. call_type: Must be from the closed enum. Pick the PRIMARY purpose. If a call covers multiple topics, use the one that drove the call.

3. value_type:
   - "durable": Contains reusable knowledge — technical fixes, process steps, configuration details, policy clarifications, contact info. Useful 6+ months from now.
   - "ephemeral": Time-bound — appointment scheduling, status checks, one-off troubleshooting that won't recur. Useful only for "what happened on X date?" queries.
   - "noise": No intelligence value — hangups, wrong numbers, sub-substantive exchanges.

4. extracted_facts: Only include facts someone searching 6 months from now would find useful. "Caller's name is Katie" is NOT a fact. "Bad table file can be fixed by restarting the system" IS a fact. Each fact needs at least one general/category-level scope alongside entity-specific scopes.

5. about_entities: The entity TYPE is who they are in the B4ALL ecosystem (operator, applicant, agency, program, internal_dept, vendor). An LSID is NOT an entity type — it's an identifier for an operator. Capture identifiers in the identifiers object. Always try to identify the LSID or client_id when a caller says "I'm from [location]" or gives a code.

6. participants: Capture the B4ALL agent and the caller at minimum. authority_on_topic = "high" for B4ALL agents explaining procedure, "medium" for operators describing their own experience, "low" for callers relaying secondhand info.

7. unresolved_questions: Capture anything asked but not answered — "I'll call you back", "let me check on that", questions where the agent didn't have the answer. These surface follow-up gaps.

8. signal_types: Must be from the closed set. Select all that apply.

9. summary: Write for a search engine. Include LSIDs, identifier codes, specific topics, and outcomes. Make the summary findable by someone who doesn't know this call exists.

10. relationship_summary: Required for operator and agency calls. Optional for internal calls. NULL for applicant and unknown calls. Examples: "FedEx Print AKE is a single-location franchise operator in CA" or "Saratoga County Sheriff dispatch hub connecting 4+ LiveScan locations in NY".`;

const DIALPAD_VARIANT = `SOURCE-SPECIFIC CONTEXT:
You are receiving a Dialpad call record. Dialpad provides an AI-generated recap (summary) and structured outcome metadata.

- Existing recap outcome: {recap_outcome}
- Existing recap purposes: {recap_purposes}
- Existing call dispositions: {call_dispositions}

DIALPAD-SPECIFIC RULES:
11. The AI recap is reliable for topic and outcome but may miss specific identifiers (LSIDs, ATIs, TCNs) and reusable technical details. Use the recap as your primary source, but extract identifiers and facts from the transcript if provided.
12. If recap_outcome is provided, use it to inform resolution_status but verify against the recap text. "Assistance provided" ≈ resolved. "Follow up" ≈ partially_resolved. "Transferred" ≈ transferred.
13. If recap_purposes is provided, use it to inform call_type and signal_types. "Technical Support" → support_request + device_issue. "Billing Questions" → billing_inquiry + billing_event.`;

const GOTO_VARIANT = `SOURCE-SPECIFIC CONTEXT:
You are receiving a GoTo Connect call record. GoTo was B4ALL's phone system before February 2026 (now decommissioned). All data is historical.

An AI-generated summary from a prior pipeline is provided as primary input.

GOTO-SPECIFIC RULES:
11. The AI summary is well-structured and reliable. Use it as your primary source.
12. If raw transcript is also provided, it may contain extensive IVR menu prompts ("Press 2 for customer support", "Please press 3 if you are in California" repeated 20+ times). IGNORE all IVR content entirely. Extract only from the human conversation portion.
13. GoTo calls predate the current phone system. Historical context is still valuable for technical fixes and process knowledge, but time-bound information (specific appointments, transaction statuses) is ephemeral.`;

const BLAND_VARIANT = `SOURCE-SPECIFIC CONTEXT:
You are receiving a Bland AI agent call. "Alex" is B4ALL's AI receptionist. The caller is speaking to an AI, not a human agent.

Vendor analysis is provided but NOT fully reliable:
- Vendor persona: {bland_persona} (WARNING: ~40% error rate on "operator" label. RE-CLASSIFY from transcript.)
- Vendor topic: {topic_label}
- Escalated: {escalated}
- Transfer target: {transfer_target}
- Call quality: {call_quality}

BLAND-SPECIFIC RULES:
11. DO NOT trust the vendor persona classification. Classify caller_persona from what the caller actually says and does. Use caller_persona_reasoning to explain your classification.
12. Alex's responses are TEMPLATED. Do NOT extract facts from Alex's scripted dialogue (e.g., "go to ApplicantServices.com", "you'll need your Payment ID"). These are standard scripts, not novel information. Only extract facts from: (a) the CALLER's statements, or (b) novel information Alex provides in direct response to a specific question.
13. For transferred calls: focus extraction on what happened BEFORE the transfer. Post-transfer content is typically silence or hold music.
14. The vendor's topic_label and escalated/transfer_target fields ARE reliable. Use them as supporting context for your classification.
15. If the call is a simple applicant scheduling/status inquiry handled entirely by Alex with no novel information, classify as value_type="ephemeral" and extract no facts.`;

/** Build the full system prompt for a given source */
export function buildSystemPrompt(sourceSystem: string): string {
  switch (sourceSystem) {
    case "dialpad":
      return SHARED_BASE + "\n\n" + DIALPAD_VARIANT;
    case "goto":
      return SHARED_BASE + "\n\n" + GOTO_VARIANT;
    case "bland":
      return SHARED_BASE + "\n\n" + BLAND_VARIANT;
    default:
      return SHARED_BASE;
  }
}

/** Build the user message with call metadata and tiered content */
export function buildUserMessage(call: CallRecord): string {
  const lines: string[] = [];

  lines.push(`CALL METADATA:`);
  lines.push(`- Source: ${call.source_system}`);
  lines.push(`- Direction: ${call.direction}`);
  lines.push(`- Date: ${call.source_timestamp}`);
  lines.push(`- Duration: ${call.duration_seconds}s`);
  lines.push(`- Caller: ${call.caller_name} (${call.caller_phone})`);
  lines.push(`- Agent: ${call.agent_name}`);

  // Source-specific metadata
  if (call.source_system === "dialpad") {
    if (call.recap_outcome) lines.push(`- Existing recap outcome: ${call.recap_outcome}`);
    if (call.recap_purposes?.length) lines.push(`- Existing recap purposes: ${call.recap_purposes.join(", ")}`);
    if (call.call_dispositions) lines.push(`- Existing call dispositions: ${call.call_dispositions}`);
  } else if (call.source_system === "bland") {
    if (call.bland_persona) lines.push(`- Vendor persona: ${call.bland_persona} (WARNING: may be incorrect)`);
    if (call.topic_label) lines.push(`- Vendor topic: ${call.topic_label}`);
    if (call.escalated !== undefined) lines.push(`- Escalated: ${call.escalated}`);
    if (call.transfer_target) lines.push(`- Transfer target: ${call.transfer_target}`);
    if (call.call_quality) lines.push(`- Call quality: ${call.call_quality}`);
  }

  // Call content — tiered input
  lines.push(``);
  lines.push(`CALL CONTENT:`);

  if (call.source_system === "dialpad" && call.ai_recap) {
    lines.push(call.ai_recap);
    if (call.transcript_text) {
      lines.push(``);
      lines.push(`TRANSCRIPT (for identifier extraction):`);
      lines.push(call.transcript_text.slice(0, 3000));
    }
  } else if (call.source_system === "goto" && call.ai_summary) {
    lines.push(call.ai_summary);
    if (call.transcript_text) {
      lines.push(``);
      lines.push(`TRANSCRIPT (may contain IVR noise — ignore IVR):`);
      lines.push(call.transcript_text.slice(0, 3000));
    }
  } else if (call.source_system === "bland") {
    if (call.bland_summary) lines.push(call.bland_summary);
    if (call.transcript_text) {
      lines.push(``);
      lines.push(`TRANSCRIPT:`);
      lines.push(call.transcript_text.slice(0, 2000));
    }
  } else {
    // Fallback: use whatever text is available
    const text = call.transcript_text || call.text_content || "";
    lines.push(text.slice(0, 3000));
  }

  return lines.join("\n");
}

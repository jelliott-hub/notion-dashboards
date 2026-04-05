// supabase/functions/extract-call-intelligence/lib/types.ts

/** Raw call record from any source, normalized for processing */
export interface CallRecord {
  call_key: string;
  source_system: "dialpad" | "goto" | "bland";
  source_id: string;
  source_timestamp: string;
  direction: string;
  duration_seconds: number;
  agent_name: string;
  caller_name: string;
  caller_phone: string;
  text_content: string;
  has_transcript: boolean;
  vendor_metadata: Record<string, unknown>;

  // Source-specific fields for input assembly
  ai_recap?: string;
  recap_outcome?: string;
  recap_purposes?: string[];
  call_dispositions?: string;
  ai_summary?: string;
  bland_summary?: string;
  bland_persona?: string;
  topic_label?: string;
  escalated?: boolean;
  transfer_target?: string;
  call_quality?: string;
  transcript_text?: string;
}

/** Result of pre-filter check */
export interface FilterResult {
  pass: boolean;
  skipped_reason?: string;
}

/** LLM extraction output — matches the JSON the prompt produces */
export interface ExtractionOutput {
  caller_persona: string;
  call_type: string;
  call_intent: string;
  resolution_status: string;
  value_type: string;
  specificity: string;
  classification_confidence: number;
  summary: string;
  relationship_summary: string | null;
  caller_persona_reasoning: string;
  participants: Array<{
    name: string;
    role: string;
    is_b4all: boolean;
    authority_on_topic: string;
  }>;
  about_entities: Array<{
    name: string;
    type: string;
    role: string;
    client_id: string | null;
    confidence: number;
    identifiers: {
      lsid: string | null;
      blsid: string | null;
      ori: string | null;
      ati: string | null;
      tcn: string | null;
    };
  }>;
  extracted_facts: Array<{
    fact: string;
    scope: string[];
    stated_by: string;
    fact_type: string;
    confidence: number;
  }>;
  signal_types: string[];
  unresolved_questions: string[];
  discrepancies: string[];
}

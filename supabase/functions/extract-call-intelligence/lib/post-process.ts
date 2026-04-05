// supabase/functions/extract-call-intelligence/lib/post-process.ts
import type { ExtractionOutput } from "./types.ts";

/**
 * Resolve entity identifiers to client_ids via lookup.find_customer().
 * Returns updated entities with client_ids filled in, plus matched_client_ids array.
 */
export async function resolveEntities(
  // deno-lint-ignore no-explicit-any
  conn: { queryObject: (query: string, args?: any[]) => Promise<{ rows: Array<Record<string, unknown>> }> },
  extraction: ExtractionOutput
): Promise<{ entities: ExtractionOutput["about_entities"]; matchedClientIds: string[] }> {
  const resolvedEntities = [...extraction.about_entities];
  const clientIds = new Set<string>();

  for (let i = 0; i < resolvedEntities.length; i++) {
    const entity = resolvedEntities[i];

    // Build search terms from identifiers first, then entity name for operators
    const searchTerms: string[] = [];
    if (entity.identifiers?.lsid) searchTerms.push(entity.identifiers.lsid);
    if (entity.identifiers?.blsid) searchTerms.push(entity.identifiers.blsid);
    if (entity.identifiers?.ori) searchTerms.push(entity.identifiers.ori);
    if (entity.client_id) searchTerms.push(entity.client_id);

    // Fall back to entity name for operator entities
    if (searchTerms.length === 0 && entity.name && entity.type === "operator") {
      searchTerms.push(entity.name);
    }

    for (const term of searchTerms) {
      try {
        const result = await conn.queryObject<{ client_id: string }>(
          `SELECT client_id FROM lookup.find_customer($1) LIMIT 1`,
          [term]
        );
        if (result.rows.length > 0 && result.rows[0].client_id) {
          resolvedEntities[i] = { ...entity, client_id: result.rows[0].client_id as string };
          clientIds.add(result.rows[0].client_id as string);
          break;
        }
      } catch {
        // lookup.find_customer may not match — that's fine, leave client_id null
      }
    }
  }

  return {
    entities: resolvedEntities,
    matchedClientIds: Array.from(clientIds),
  };
}

# External Action Firewall — v2 (Microsoft-Hardened)

**Date:** 2026-03-31
**Author:** Claude (revised from Jack's v1 spec)
**Scope:** Microsoft Graph surfaces only (Outlook, Teams, SharePoint). HubSpot and Bland excluded per Jack's direction.
**Status:** Ready for review

---

## What Changed From v1

v1 designed a generic denylist + trigger system across all external systems. This revision **zooms in on Microsoft** and addresses 7 specific gaps found during the live data audit. The generic infrastructure (denylist table, check function) remains, but the Microsoft-specific hardening layers are new.

### Gaps Found in v1

| # | Gap | Severity | v2 Fix |
|---|------|----------|--------|
| 1 | 4 live delete rules already deployed in Outlook | **CRITICAL** | Phase 0: manual cleanup |
| 2 | `ref_opportunity_type.has_actuator` still `true` for `auto_delete` | **CRITICAL** | Phase 0: immediate flip |
| 3 | `fact_execution` has zero Microsoft actions — trigger provides no protection | HIGH | Remove from Microsoft scope; focus enforcement on `queue_review` |
| 4 | `proposed_config` JSON is the real payload, not `action` column | HIGH | Deep JSON inspection trigger |
| 5 | MS Graph destructive actions beyond `"delete"` (`permanentDelete`, `moveToFolder → DeletedItems`, `redirectTo`) | HIGH | Expanded denylist + JSON inspection |
| 6 | `create-inbox-rules` Edge Function has no pre-flight check | HIGH | Application-layer allowlist |
| 7 | Teams/SharePoint have zero coverage | MEDIUM | Future-proofing denylist entries + convention |

---

## Phase 0: Immediate Triage (Do Today, Before Any Code)

These are live risks. No migration needed — just manual actions.

### 0a. Reject the 7 pending delete proposals

```sql
UPDATE automations.queue_review
SET status = 'rejected',
    reviewed_by = 'jack',
    reviewed_at = now(),
    review_notes = 'Bulk rejected: auto_delete proposals blocked by firewall policy. No automated deletion of external emails permitted.'
WHERE id IN (261, 262, 263, 264, 265, 266, 267)
  AND status = 'proposed';
```

These target the accounting mailbox and would auto-delete emails from:
- `Debra.Powers@baycare.org`
- `OLeyvaLeonor@lbschools.net`
- `Wendy.Eychner@hrd.cccounty.us`
- `cgonzalez@interactivebrokers.com`
- `store6011@theupsstore.com`
- `cbarteau@buttecounty.net`
- `debbiep@fsusd.org`

### 0b. Flip the actuator kill switch

```sql
UPDATE automations.ref_opportunity_type
SET has_actuator = false
WHERE opportunity_type = 'auto_delete';
```

This prevents `deploy-automation` from ever picking up an `auto_delete` proposal, even if one somehow gets approved.

### 0c. Audit the 4 live delete rules in Outlook

These rules are currently active and permanently deleting matching emails:

| Rule ID | Mailbox | Display Name | Condition | Risk Assessment |
|---------|---------|-------------|-----------|-----------------|
| `AQAAAhtssSo=` | accounting | guest_signer | Subject contains "@no.reply Has Signed Your Document" | **REVIEW** — deleting PandaDoc signing notifications. Could miss completed contract alerts. |
| `AQAABqT1fgk=` | sales | Junk: GamesBeat | Sender = `INFO@GAMESBEAT.NET` | LOW — spam. But should be move-to-junk, not delete. |
| `AQAAB2wDPmc=` | support | -Temu Pallets- | From `nieuwsbriefysyxf@OscK.studio1509.com` | LOW — obvious spam. Same recommendation: move, don't delete. |
| `AQAAB2wDPnM=` | support | SEP SBE Alerts | From `alerts@spn.com` | LOW — alert noise. Same recommendation. |

**Recommended action:** Convert all 4 from `{"delete": true}` to `{"moveToFolder": "Junk Email"}` via the MS Graph `PATCH /mailFolders/inbox/messageRules/{id}` endpoint. This preserves the routing behavior without permanent data loss.

**The `guest_signer` rule is the most concerning** — it's silently deleting PandaDoc completion notifications in the accounting inbox. If a contract signing notification gets eaten, nobody knows the deal closed.

### 0d. Note the forwardTo rules (no action needed, just awareness)

The accounting mailbox has 10+ `forwardTo` rules forwarding invoices to `biometrics4all@ap.ramp.com`. These are **legitimate** (Ramp AP automation) but represent the exfiltration vector: a malicious `forwardTo` rule could silently copy emails to an external address. Phase 1 addresses this with the allowlist.

---

## Phase 1: Database-Level Enforcement

### Object 1: `meta.cfg_forbidden_external_actions` (unchanged from v1)

Same table design. One addition to the seed data:

#### Seed Data — Microsoft-Specific Entries

In addition to the global `*` entries from v1, add:

| system | verb | reason |
|--------|------|--------|
| `outlook` | `auto_delete` | Outlook-specific: no automated inbox delete rules |
| `outlook` | `permanentDelete` | Outlook-specific: no permanent delete actions |
| `outlook` | `redirectTo` | Outlook-specific: no silent email redirects (exfiltration risk) |
| `outlook` | `moveToDeletedItems` | Outlook-specific: no move-to-trash as delete substitute |
| `teams` | `delete_channel` | Teams-specific: no channel deletion |
| `teams` | `remove_member` | Teams-specific: no member removal |
| `teams` | `delete_message` | Teams-specific: no message deletion |
| `sharepoint` | `delete_item` | SharePoint-specific: no file/item deletion |
| `sharepoint` | `delete_site` | SharePoint-specific: no site deletion |

### Object 2: `meta.check_external_action()` (unchanged from v1)

Same function. Edge Functions call this before API calls.

### Object 3: `meta.enforce_no_forbidden_action_outlook() → trigger function` (NEW — replaces generic trigger for queue_review)

This is **Microsoft-specific** and does deep inspection. It replaces the generic `enforce_no_forbidden_action()` for the `queue_review` table.

```
BEFORE INSERT OR UPDATE ON automations.queue_review
FOR EACH ROW
WHEN (NEW.source_system = 'outlook')
```

**What it checks:**

1. **Top-level action column** — `NEW.action` against the denylist (same as v1)

2. **`proposed_config` JSON deep inspection:**
   - `NEW.proposed_config->>'action'` — the action verb inside the JSON payload
   - `NEW.proposed_config->>'delete'` — MS Graph delete flag
   - `NEW.proposed_config->>'permanentDelete'` — MS Graph permanent delete flag
   - `NEW.proposed_config->>'redirectTo'` — MS Graph redirect action
   - `NEW.proposed_config->'proposed_rule'->>'action'` — nested proposed_rule action (some proposals nest it)

3. **Target folder inspection:**
   - If `NEW.proposed_config->>'action' = 'move_to_folder'`:
     - Check if `NEW.target_folder` or `NEW.proposed_config->>'target_folder'` matches `'Deleted Items'`, `'DeletedItems'`, or folder IDs known to be Deleted Items folders
     - This catches the "move_to_folder as delete substitute" pattern

4. **forwardTo allowlist:**
   - If `NEW.proposed_config` contains a `forwardTo` key:
     - Extract the target email address
     - Check against `meta.cfg_allowed_forward_targets` (new small config table — see Object 6)
     - If the target is not in the allowlist, RAISE EXCEPTION

**If any check fails:**
```
RAISE EXCEPTION 'BLOCKED: Outlook action "%" with config "%" is forbidden by meta.cfg_forbidden_external_actions. Rule: %. Contact Jack to review.',
  NEW.action, NEW.proposed_config::text, <matched_rule_reason>;
```

### Object 4: `meta.protect_denylist()` (unchanged from v1)

Self-protection trigger on `cfg_forbidden_external_actions`. No changes.

### Object 5: `ref_opportunity_type` update (unchanged from v1, but already done in Phase 0)

`has_actuator = false` for `auto_delete`.

### Object 6: `meta.cfg_allowed_forward_targets` (NEW)

Small allowlist table for permitted `forwardTo` destinations.

| Column | Type | Nullable | Business Meaning |
|--------|------|----------|-----------------|
| `email_address` | text | NOT NULL | Allowed forward target (exact match, lowercased) |
| `system` | text | NOT NULL | Which system this applies to (`outlook`, `*`) |
| `reason` | text | NOT NULL | Why this target is allowed |
| `created_at` | timestamptz | NOT NULL, default `now()` | When added |
| `created_by` | text | NOT NULL, default `'system'` | Who added it |

**Primary key:** `(system, email_address)`

**Seed data:**

| system | email_address | reason |
|--------|--------------|--------|
| `outlook` | `biometrics4all@ap.ramp.com` | Ramp AP automation — invoice forwarding |
| `outlook` | `support@biometrics4all.com` | Internal support forwarding |
| `outlook` | `accounting@biometrics4all.com` | Internal accounting forwarding |

**Self-protection:** Same DELETE trigger pattern as `cfg_forbidden_external_actions`.

Any `forwardTo` rule targeting an address NOT in this table will be blocked. This prevents the exfiltration vector — a malicious or misconfigured rule can't silently forward emails to an external address.

### Object 7: `meta.cfg_allowed_outlook_folders` (NEW)

Allowlist of folders that `move_to_folder` rules may target.

| Column | Type | Nullable | Business Meaning |
|--------|------|----------|-----------------|
| `folder_name` | text | NOT NULL | Folder display name (lowercased) |
| `mailbox` | text | NOT NULL | Which mailbox (`*` for all) |
| `reason` | text | NOT NULL | Why this folder is allowed |
| `created_at` | timestamptz | NOT NULL, default `now()` | When added |

**Primary key:** `(mailbox, folder_name)`

**Seed data:** Populated from currently deployed rules:

| mailbox | folder_name | reason |
|---------|------------|--------|
| `*` | `notifications` | Standard routing — low-priority notifications |
| `*` | `junk email` | Standard routing — spam/junk filtering |
| `accounting` | `inbox/ramp/invoices` | Ramp invoice processing |
| `accounting` | `inbox/panda docs/loaner agreement` | PandaDoc loaner agreements |
| `accounting` | `inbox/panda docs/sam agreement` | PandaDoc SAM agreements |
| `support` | `inbox/junk mail removed by rules` | Support junk filtering |
| `support` | `inbox/junk e-mail` | Support junk filtering (legacy folder name) |

Any `move_to_folder` rule targeting a folder NOT in this table will be blocked. This prevents "move to Deleted Items" as a delete workaround and ensures new folder targets require explicit approval.

---

## Phase 1.5: Edge Function Hardening

This is where v2 fundamentally diverges from v1. Database triggers are necessary but not sufficient. The `create-inbox-rules` Edge Function is the actual execution surface.

### `create-inbox-rules` — Required Changes

**Current behavior:** Reads approved `queue_review` proposals, translates `proposed_config` into MS Graph `POST /mailFolders/inbox/messageRules` calls.

**Required changes:**

1. **Pre-flight database check:**
   ```typescript
   // Before ANY Graph API call:
   const { data: allowed } = await supabase
     .rpc('check_external_action', {
       p_system: 'outlook',
       p_verb: proposedConfig.action
     });

   if (!allowed) {
     throw new Error(`BLOCKED: Action "${proposedConfig.action}" forbidden by firewall`);
   }
   ```

2. **Hardcoded action allowlist (belt + suspenders):**
   ```typescript
   const ALLOWED_RULE_ACTIONS = ['moveToFolder', 'markAsRead', 'markImportance', 'stopProcessingRules'];
   const FORBIDDEN_RULE_ACTIONS = ['delete', 'permanentDelete', 'forwardTo', 'redirectTo', 'forwardAsAttachmentTo'];

   // Check the actual Graph API payload being constructed:
   for (const key of Object.keys(ruleActions)) {
     if (FORBIDDEN_RULE_ACTIONS.includes(key)) {
       throw new Error(`BLOCKED: Graph rule action "${key}" is permanently forbidden`);
     }
     if (!ALLOWED_RULE_ACTIONS.includes(key)) {
       throw new Error(`BLOCKED: Graph rule action "${key}" is not in the allowlist — requires code change to permit`);
     }
   }
   ```

   Note: `forwardTo` is on the FORBIDDEN list for the Edge Function even though legitimate forwarding rules exist. Those existing rules were created manually in Outlook, not through the Hub automation. If the Hub ever needs to create forwarding rules, it should go through a separate, audited code path that checks `meta.cfg_allowed_forward_targets`.

3. **Target folder validation:**
   ```typescript
   // If action is moveToFolder, validate the target:
   const { data: folderAllowed } = await supabase
     .from('meta.cfg_allowed_outlook_folders')
     .select('folder_name')
     .or(`mailbox.eq.${mailbox},mailbox.eq.*`)
     .eq('folder_name', targetFolder.toLowerCase());

   if (!folderAllowed?.length) {
     throw new Error(`BLOCKED: Folder "${targetFolder}" is not in the approved folder allowlist`);
   }
   ```

4. **Execution logging:**
   ```typescript
   // After successful rule creation, log to fact_execution:
   await supabase.from('automations.fact_execution').insert({
     action: 'create_inbox_rule',
     rule_name: `outlook_rule_${proposal.id}`,
     target_system: 'outlook',
     payload: { mailbox, ruleActions, conditions, graphRuleId },
     status: 'success'
   });
   ```

   This closes the logging gap — Outlook actions will now appear in `fact_execution` with `target_system = 'outlook'`.

### `deploy-automation` — Required Changes

The actuator dispatcher should:

1. **Check `has_actuator` on `ref_opportunity_type` before dispatching** (it may already do this — verify)
2. **Never dispatch `auto_delete` type proposals**, even if `has_actuator` is somehow flipped back to `true`:
   ```typescript
   const PERMANENTLY_BLOCKED_TYPES = ['auto_delete'];
   if (PERMANENTLY_BLOCKED_TYPES.includes(proposal.opportunity_type)) {
     // Log and skip, don't throw — we don't want the actuator to crash
     await logBlocked(proposal, 'opportunity_type permanently blocked by firewall policy');
     continue;
   }
   ```

---

## Phase 2: Teams & SharePoint Future-Proofing

There are currently 2 read-only Edge Functions touching Teams (`sync-teams`, `sync-teams-chats`). Neither writes. But the convention must be established now so that when someone builds a Teams-writing Edge Function, the guardrails are already in place.

### Convention: "Write Functions Require Firewall Clearance"

Add to `meta.cfg_edge_function`:

| slug | domain | action_type | write_target | firewall_required |
|------|--------|-------------|-------------|-------------------|
| `sync-teams` | `data_pipeline` | `sync_data` | `null` | `false` |
| `sync-teams-chats` | `data_pipeline` | `sync_data` | `null` | `false` |
| `create-inbox-rules` | `email_intelligence` | `deploy_automation` | `outlook` | **`true`** |

New columns on `cfg_edge_function`:
- `write_target` (text, nullable) — which external system this function writes to. `null` = read-only.
- `firewall_required` (boolean, default `false`) — whether this function must call `meta.check_external_action()` before external API calls.

Any Edge Function with `write_target IS NOT NULL` and `firewall_required = false` should be flagged in a nightly audit query.

### `meta.v_unprotected_write_functions` (view)

```sql
CREATE VIEW meta.v_unprotected_write_functions AS
SELECT slug, domain, action_type, write_target
FROM automations.cfg_edge_function
WHERE write_target IS NOT NULL
  AND firewall_required = false;
```

If this view ever returns rows, something needs attention.

---

## Revised Folder Scaffold

```
external-action-firewall/
├── README.md
├── phase-0-triage/
│   ├── 000_reject_pending_deletes.sql        # Reject queue_review IDs 261-267
│   ├── 001_disable_auto_delete_actuator.sql  # has_actuator = false
│   └── 002_audit_live_delete_rules.md        # Manual: convert 4 Outlook rules from delete → move
│
├── migrations/
│   ├── 001_create_cfg_forbidden.sql          # meta.cfg_forbidden_external_actions + self-protection
│   ├── 002_seed_denylist.sql                 # Global + Microsoft-specific seed data
│   ├── 003_create_cfg_allowed_forwards.sql   # meta.cfg_allowed_forward_targets + self-protection
│   ├── 004_create_cfg_allowed_folders.sql    # meta.cfg_allowed_outlook_folders + self-protection
│   ├── 005_create_check_function.sql         # meta.check_external_action()
│   ├── 006_create_outlook_trigger.sql        # meta.enforce_no_forbidden_action_outlook() on queue_review
│   ├── 007_add_edge_function_columns.sql     # write_target + firewall_required on cfg_edge_function
│   ├── 008_create_unprotected_view.sql       # meta.v_unprotected_write_functions
│   ├── 009_add_target_system_to_fact.sql     # ADD COLUMN target_system to fact_execution
│   └── 010_register_meta.sql                 # object_registry + column_dictionary entries
│
├── edge-functions/
│   ├── create-inbox-rules/
│   │   └── CHANGES.md                        # Pre-flight check + allowlist + folder validation + logging
│   └── deploy-automation/
│       └── CHANGES.md                        # Permanently blocked types list
│
└── validation/
    ├── smoke_tests.sql                       # INSERTs that should FAIL + SELECTs that should PASS
    ├── verify_no_live_deletes.sql            # Query inbox_rules for any remaining delete:true rules
    └── verify_unprotected_functions.sql      # Query v_unprotected_write_functions (should return 0 rows)
```

---

## Execution Order

| Step | What | Blocks On | Estimated Effort |
|------|------|-----------|-----------------|
| **Phase 0a** | Reject 7 pending proposals | Nothing — do now | 2 min |
| **Phase 0b** | Flip `has_actuator` | Nothing — do now | 1 min |
| **Phase 0c** | Convert 4 delete rules to move-to-junk | Need Graph API call or manual Outlook admin | 15 min |
| **Phase 1 migrations 001-006** | Database objects + triggers | Phase 0 complete | 1 hour |
| **Phase 1 migrations 007-010** | Edge function metadata + fact_execution column | 001-006 complete | 30 min |
| **Phase 1.5** | Harden `create-inbox-rules` + `deploy-automation` | 001-006 deployed + Edge Function source code access | 2 hours |
| **Phase 2** | Teams/SharePoint conventions | Phase 1 complete | 30 min |
| **Validation** | Run all smoke tests | Everything deployed | 30 min |

---

## Defense-in-Depth Summary (Microsoft)

After full deployment, a destructive Outlook action must bypass ALL of these layers to execute:

```
Layer 1: ref_opportunity_type.has_actuator = false
  → deploy-automation won't pick up auto_delete proposals

Layer 2: deploy-automation hardcoded PERMANENTLY_BLOCKED_TYPES
  → Even if has_actuator is flipped, actuator refuses auto_delete

Layer 3: queue_review BEFORE INSERT trigger
  → Checks action column against denylist
  → Deep-inspects proposed_config JSON for delete/permanentDelete/redirectTo
  → Validates target folders against allowlist
  → Validates forwardTo targets against allowlist

Layer 4: meta.check_external_action() called by Edge Function
  → Application-layer check before Graph API call

Layer 5: create-inbox-rules hardcoded FORBIDDEN_RULE_ACTIONS
  → Even if database check passes, Edge Function refuses delete/permanentDelete/forwardTo/redirectTo

Layer 6: create-inbox-rules ALLOWED_RULE_ACTIONS allowlist
  → Only moveToFolder/markAsRead/markImportance/stopProcessingRules permitted
  → Any new Graph action type requires a code change to permit

Layer 7: Target folder allowlist validation
  → moveToFolder can only target pre-approved folders
  → "Deleted Items" as a move target is blocked

Layer 8: meta.v_unprotected_write_functions audit view
  → Any new Edge Function with write_target that lacks firewall_required = true is flagged
```

For a destructive action to reach Outlook, an attacker or bug would need to:
1. Re-enable `has_actuator` on `auto_delete` (requires DB write to config table)
2. Bypass the actuator's hardcoded block list (requires Edge Function code change)
3. Insert a proposal that passes the trigger's JSON deep inspection (requires understanding the trigger logic)
4. Have the Edge Function's `check_external_action()` return true (requires modifying the denylist, which has a DELETE protection trigger)
5. Pass the Edge Function's hardcoded forbidden actions list (requires code change)
6. Pass the Edge Function's allowlist (requires code change)
7. Target a folder in the approved list (requires DB write to allowlist table, which has DELETE protection)

That's 7 independent layers. Any single layer stopping the action is sufficient.

---

## Open Items

1. **`queue_draft` column audit** — v1 flagged this. It uses `proposed_action`, not `action`. For Microsoft scope, this table is irrelevant (it's ticket email drafts, not Outlook rule proposals). Deprioritize.

2. **Phase 0c execution** — Someone needs to make the Graph API calls to convert the 4 delete rules. Either:
   - Build a one-off Edge Function that PATCHes the rules
   - Do it manually through Outlook admin / Exchange admin center
   - Extend `create-inbox-rules` to support PATCH operations (heavier lift)

3. **`fact_execution.target_system` column** — Migration 009 adds this. Existing rows will have `null`. Backfill is optional but recommended for auditability.

4. **Nightly audit alert** — Consider a pg_cron job that checks `v_unprotected_write_functions` and `inbox_rules WHERE delete = true` and writes to `meta.agent_log` if either returns rows.

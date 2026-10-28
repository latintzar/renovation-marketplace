# Test Matrix — Leo Project Lifecycle

**Date:** 2026-04-15
**Flow:** Quote → Agreement → Payment → Milestones → Completion → Review
**Files read:** routes/{milestones,variations,projects,reviews,messages,documents,dispute,payment,canvas}.py, shared/{auth,states,sandbox,db}.py, tests/conftest.py

---

## State Machine

```
Project:   finalized → paid → in_progress → complete
                                          ↘ cancelled (guard: no milestone past pending)

Milestone: pending → proof_submitted → released
                   ↘ disputed (via dispute/open)

Variation: pending → approved | declined
```

**Actors:** contractor (JWT), homeowner (JWT), unauthenticated, wrong-contractor, wrong-homeowner

---

## Variation Matrix

### File: test_lifecycle.py — Happy path (3 milestones)

| #  | Test name                                | Starting state     | Actions                                              | Expected                                      |
|----|------------------------------------------|--------------------|------------------------------------------------------|-----------------------------------------------|
| 1  | test_lifecycle_3ms_happy_path_completes  | new                | finalize → consent → checkout → proof×3 → release×3  | status=complete, 3 transfers, completed_at set |
| 2  | test_lifecycle_3ms_review_after_complete | completed (from 1) | POST review (rating=5, body)                          | review stored, contractor avg_rating updated   |
| 3  | test_lifecycle_invoice_after_complete    | completed          | GET /documents/{token}/invoice                        | 200 HTML with milestone data                   |
| 4  | test_lifecycle_project_status_progression| new                | check status after each step                          | finalized→paid→in_progress→complete            |

### File: test_milestones.py — Milestone phase variations (3-5 milestones)

| #  | Test name                                 | Starting state        | Actions                                    | Expected                                       |
|----|-------------------------------------------|-----------------------|--------------------------------------------|-------------------------------------------------|
| 5  | test_milestone_proof_advances_to_in_progress | paid, 3ms          | submit proof on m0                         | project status=in_progress, m0=proof_submitted  |
| 6  | test_milestone_reject_resubmit_approve    | paid, 3ms             | proof m0 → dispute → proof m0 again → release | m0=released, dispute recorded                 |
| 7  | test_milestone_release_creates_transfer   | paid+proof on m0      | release m0                                 | Stripe transfer created, m0=released            |
| 8  | test_milestone_last_release_completes     | paid, 3ms, m0+m1 released | release m2                            | status=complete, completed_at set               |
| 9  | test_milestone_double_release_idempotent  | paid, m0 released     | release m0 again                           | 409 (already released)                          |
| 10 | test_milestone_invalid_index              | paid, 3ms             | proof on idx=99                            | 400 invalid milestone index                     |
| 11 | test_milestone_proof_on_unpaid            | unpaid                | proof on m0                                | 400 not paid                                    |
| 12 | test_milestone_5ms_full_cycle             | paid, 5ms             | proof+release ×5                           | complete, 5 transfers                           |

### File: test_variations.py — Change orders

| #  | Test name                                 | Starting state        | Actions                                    | Expected                                        |
|----|-------------------------------------------|-----------------------|--------------------------------------------|--------------------------------------------------|
| 13 | test_variation_create_approve             | paid, in_progress     | create variation → approve                 | variation=approved, checkout_session created      |
| 14 | test_variation_create_decline             | paid, in_progress     | create variation → decline                 | variation=declined, notification sent             |
| 15 | test_variation_already_actioned           | variation=approved    | approve again                              | 409 already actioned                             |
| 16 | test_variation_wrong_project              | paid                  | approve with mismatched token              | 400 variation does not belong                    |
| 17 | test_variation_not_found                  | paid                  | approve non-existent variation             | 404                                              |

### File: test_completion.py — Post-completion

| #  | Test name                                 | Starting state        | Actions                                    | Expected                                        |
|----|-------------------------------------------|-----------------------|--------------------------------------------|--------------------------------------------------|
| 18 | test_review_creates_and_updates_rating    | completed             | POST review rating=4                       | review stored, avg_rating=4.0, review_count=1    |
| 19 | test_review_duplicate_rejected            | completed+reviewed    | POST review again                          | 409 already submitted                            |
| 20 | test_review_on_incomplete_rejected        | paid (not complete)   | POST review                                | 400 not complete                                 |
| 21 | test_review_rating_validation             | completed             | POST review rating=0 / rating=6            | 400 rating out of range                          |
| 22 | test_invoice_only_after_complete          | paid                  | GET invoice                                | 400 not complete                                 |
| 23 | test_agreement_html_renders               | finalized             | GET agreement                              | 200 HTML with contractor/homeowner data          |
| 24 | test_consent_records_hash                 | finalized             | POST record-consent                        | consent_id returned, document_hash set           |

### File: test_messages.py — Chat

| #  | Test name                                 | Starting state        | Actions                                    | Expected                                        |
|----|-------------------------------------------|-----------------------|--------------------------------------------|--------------------------------------------------|
| 25 | test_message_contractor_sends             | paid                  | send from contractor                       | 200, message in DB                               |
| 26 | test_message_homeowner_sends              | paid                  | send from homeowner                        | 200, message in DB                               |
| 27 | test_message_history_ordered              | paid + 3 messages     | GET messages                               | 3 messages, chronological                        |
| 28 | test_message_on_unpaid_blocked            | unpaid                | send message                               | 400 only for paid quotes                         |
| 29 | test_message_empty_body_rejected          | paid                  | send with empty body                       | 400 empty body                                   |
| 30 | test_message_invalid_role_rejected        | paid                  | send with role="admin"                     | 400 invalid role                                 |

### File: test_auth_guards.py — Auth, Role, Ownership

| #  | Test name                                      | Endpoint                           | Condition                | Expected    |
|----|-------------------------------------------------|------------------------------------|--------------------------|-------------|
| 31 | test_proof_no_auth                              | POST milestones/{idx}/proof        | No Authorization header  | 401         |
| 32 | test_proof_homeowner_forbidden                  | POST milestones/{idx}/proof        | Homeowner JWT            | 403         |
| 33 | test_proof_wrong_contractor_forbidden            | POST milestones/{idx}/proof        | Different contractor JWT | 403         |
| 34 | test_release_no_auth                            | POST milestones/{idx}/release      | No Authorization header  | 401         |
| 35 | test_release_contractor_forbidden               | POST milestones/{idx}/release      | Contractor JWT           | 403         |
| 36 | test_release_wrong_homeowner_forbidden           | POST milestones/{idx}/release      | Different homeowner JWT  | 403         |
| 37 | test_variation_create_no_auth                   | POST variations                    | No Authorization         | 401         |
| 38 | test_variation_create_homeowner_forbidden         | POST variations                    | Homeowner JWT            | 403         |
| 39 | test_variation_create_wrong_contractor_forbidden  | POST variations                    | Wrong contractor JWT     | 403         |
| 40 | test_variation_approve_no_auth                  | POST variations/{id}/approve       | No Authorization         | 401         |
| 41 | test_variation_approve_contractor_forbidden       | POST variations/{id}/approve       | Contractor JWT           | 403         |
| 42 | test_variation_decline_wrong_homeowner_forbidden  | POST variations/{id}/decline       | Wrong homeowner JWT      | 403         |
| 43 | test_cancel_no_auth                             | POST projects/{token}/cancel       | No Authorization         | 401         |
| 44 | test_cancel_wrong_user_forbidden                | POST projects/{token}/cancel       | Unrelated user JWT       | 403         |
| 45 | test_cancel_after_work_started_blocked          | POST projects/{token}/cancel       | m0=proof_submitted       | 400         |
| 46 | test_review_no_auth                             | POST projects/{token}/review       | No Authorization         | 401         |
| 47 | test_review_contractor_forbidden                | POST projects/{token}/review       | Contractor JWT           | 403         |
| 48 | test_review_wrong_homeowner_forbidden            | POST projects/{token}/review       | Wrong homeowner JWT      | 403         |
| 49 | test_project_get_unauthenticated_no_pii         | GET projects/{token}               | No auth                  | no email/phone |
| 50 | test_project_get_homeowner_sees_pii              | GET projects/{token}               | Homeowner JWT            | has email/phone|
| 51 | test_project_get_contractor_sees_pii_and_pi      | GET projects/{token}               | Contractor JWT           | has payment_intent |

---

## Fixture Requirements

| Fixture | What it provides |
|---------|-----------------|
| `contractor_jwt` | Real Supabase JWT for contractor user linked to `contractor_with_stripe` |
| `homeowner_jwt` | Real Supabase JWT for homeowner user linked to paid project |
| `wrong_contractor_jwt` | JWT for a different contractor (not assigned to project) |
| `wrong_homeowner_jwt` | JWT for a different homeowner (not the project's homeowner) |
| `paid_project_3ms` | Existing fixture — paid project with 3 milestones |
| `paid_project_5ms` | Existing fixture — paid project with 5 milestones |
| `unpaid_project` | Existing fixture — finalized but unpaid |
| `completed_project` | Existing fixture — all milestones released |

All fixtures clean up after themselves. Auth users are reused (idempotent creation).

---

## Audit Findings

1. **Milestone rejection is NOT a backend endpoint** — homeowner can only dispute (via `/dispute/open`) or release. The "reject → resubmit" flow is: homeowner opens dispute, contractor submits new proof overwriting the previous status.
2. **Variation payment webhook** — `checkout.session.completed` always patches the quote's `payment_status` and `status`, even for variation-only sessions. This could overwrite in-progress project status. Worth testing.
3. **Message endpoints have no JWT auth** — they use `sender_role` and `sender_id` in the body. Any caller can impersonate. This is a known legacy pattern, not a test target for auth guards.
4. **Dispute endpoint has no JWT auth** — uses body fields for identity. Same legacy pattern.
5. **Cancel guard is double-checked**: `assert_transition` + explicit `if status in (cancelled, complete)` — the second check catches edge cases the state machine might not.

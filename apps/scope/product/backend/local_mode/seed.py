"""Authored starter records. Financial states describe sample records, not provider receipts."""
from copy import deepcopy
from datetime import datetime, timezone
from payments.finance import compute_quote_financials

def starter(identity):
    now = datetime.now(timezone.utc).isoformat()
    contractor = identity['contractor_id']
    homeowner = identity['homeowner_id']
    quote = {'title': 'Bathroom renovation — Marbella', 'description': 'Walk-in shower conversion, tiling, new vanity and WC.', 'contractor_name': 'Marbella workshop', 'client_name': 'Homeowner', 'location': 'Marbella, Málaga', 'service_fee_percent': 5, 'created_at': '2026-01-01', 'line_items': [{'description': 'Strip-out & first fix', 'amount': 1400, 'duration_label': '3 days'}, {'description': 'Waterproofing & full-height tiling', 'amount': 2100, 'duration_label': '4 days'}, {'description': 'Fit-out & finish', 'amount': 1900, 'duration_label': '3 days'}], 'materials_upfront': 1800, 'iva_rate': 10, 'terms': ['Work guaranteed for 12 months', 'Client supplies sanitaryware unless agreed otherwise'], 'status': 'ready'}
    fin = compute_quote_financials(quote)
    assert fin.amount_total_cents == 819000
    common = {'contractor_id': contractor, 'auth_user_id': identity['contractor_auth_id'], 'homeowner_auth_id': homeowner, 'homeowner_email': 'homeowner@example.invalid', 'homeowner_phone': '', 'quote_data': quote, 'amount_total_cents': fin.amount_total_cents, 'materials_upfront_cents': fin.materials_upfront_cents, 'stripe_fee_cents': fin.fee_cents, 'iva_rate': fin.iva_rate, 'milestones': fin.milestones, 'is_sandbox': True, 'created_at': now}
    draft = {**deepcopy(common), 'id': 'quote-editable', 'token': 'sample-quote', 'status': 'finalized', 'payment_status': 'unpaid'}
    project = {**deepcopy(common), 'id': 'quote-project', 'token': 'sample-project', 'status': 'in_progress', 'payment_status': 'paid', 'started_at': now}
    project['milestones'][0]['status'] = 'proof_submitted'
    return {'contractors': [{'id': contractor, 'auth_user_id': identity['contractor_auth_id'], 'name': 'Marbella workshop', 'business_name': 'Marbella workshop', 'email': 'contractor@example.invalid', 'phone': '', 'claimed': True, 'stripe_onboarding_complete': False, 'stripe_account_id': '', 'dossier': {'trade': 'Renovation'}, 'canvas': {'business_name': 'Marbella workshop', 'trade': 'Renovation'}, 'created_at': now}], 'quotes': [draft, project], 'jobs': [], 'job_messages': [], 'milestone_updates': [{'id': 'starter-proof', 'scope_token': 'sample-project', 'milestone_index': 0, 'photos': [], 'voice_url': None, 'note': 'Strip-out and first fix ready for review.', 'status': 'proof_submitted', 'created_at': now}], 'variation_orders': [], 'notifications': [], 'reviews': []}

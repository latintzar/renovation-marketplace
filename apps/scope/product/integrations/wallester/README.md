# Wallester Card Issuing API — Service Integration Exploration

**Last updated:** 2026-04-02
**Status:** Exploratory research — no integration decision made, **no API key yet**
**Relevance to Leo Scope:** Construction materials payment controls, escrow-adjacent card issuing, tradesperson expense management
**API Docs:** `https://api-doc.wallester.com/`
**Live testing:** Not possible yet — need to sign up for Business tier first

---

## 1. What Wallester Is

Wallester AS is an Estonian-headquartered **licensed Electronic Money Institution (EMI)** and **Visa Principal Member** that provides a white-label card issuing platform. They let businesses issue branded Visa debit cards (virtual and physical) without obtaining their own banking license or Visa membership.

- **Founded:** Estonia
- **Offices:** Tallinn (HQ), Cannes (France)
- **License:** Estonian Financial Supervisory Authority (EFSA)
- **Card network:** Visa Business class
- **Scale:** 5,850+ business clients, operates in 35+ countries
- **Recognition:** Financial Times FT1000 top fintech ranking

**Core proposition:** "One integration, 30 markets" — a single REST API gives you card issuing, processing, KYC/AML, fraud monitoring, tokenization, and 3D Secure across the EEA + UK.

---

## 2. Product Tiers

Wallester operates two distinct product lines:

### Wallester Business (self-serve)
For companies that want corporate expense cards. Sign up online, verified in 24 hours, start issuing cards to employees.

### Wallester White-Label (embedded finance)
For fintechs/platforms that want to issue cards to **their own end users** under their own brand. This is the relevant tier for Leo.

| Feature | Business (self-serve) | White-Label (embedded) |
|---|---|---|
| Who holds cards | Your employees | Your platform's end users |
| Branding | Wallester + your logo | Fully your brand |
| BIN | Shared Wallester BIN | Dedicated BIN (Wallester-sponsored) |
| KYC | Wallester handles | You choose: Wallester KYC or your own |
| Integration | Dashboard / basic API | Full REST API |
| Pricing | Published tiers | Custom / negotiated |

---

## 3. Pricing

### Published Business Plans

| Plan | Monthly | Virtual Cards Included | Extra Virtual Card |
|---|---|---|---|
| Free | €0 | 300 | €0.35/mo each |
| Premium | €199/mo | 3,000 | €0.20/mo each |
| Platinum | €999/mo | 18,000 | €0.10/mo each |
| Enterprise | Custom | Custom | Custom |

### Transaction Fees

| Operation | Fee |
|---|---|
| EUR payments (POS/online) | Free (no commission) |
| ATM withdrawal (Europe) | 2% (min €2) |
| ATM withdrawal (International) | €2 + 2% |
| ATM balance inquiry | €0.50 |
| FX conversion | Visa rate + 2% |
| Physical card delivery (standard) | €5 |
| Physical card delivery (express) | €20 |
| Account top-up (bank transfer) | Free |
| Account top-up (card) | 1.2% |
| Dispute processing | €20 |
| Account closure | €25 per currency |

### White-Label Pricing
Not publicly listed — custom negotiation. Expected to include:
- Setup / integration fee
- Per-card issuance fee
- Monthly platform fee
- Transaction processing fee (interchange share)
- KYC/AML per-check fee

---

## 4. API Architecture

### Base URL & Docs
- **API Documentation:** https://api-doc.wallester.com/
- **Integration Examples:** https://github.com/wallester/integration-examples
- **Sandbox:** Private sandbox available for testing

### Authentication
Token-based authentication. Secure API key/token provisioned through the dashboard.

### Protocol
- REST API with resource-oriented URLs
- HTTP response codes for status
- JSON request/response bodies
- Webhook notifications for events (approvals, declines, etc.)

### Key Endpoints (from published examples)

```
POST   /api/v1/cards              — Issue a new card (virtual or physical)
PATCH  /api/v1/cards/{id}         — Update card settings (limits, merchant rules)
GET    /api/v1/cards/{id}         — Retrieve card details
DELETE /api/v1/cards/{id}         — Block/cancel a card

GET    /api/v1/transactions       — List transactions
GET    /api/v1/balances           — Account balances

POST   /api/v1/accounts           — Create account
POST   /api/v1/kyc                — Initiate KYC verification
```

### Example: Create a Virtual Card

```json
POST /api/v1/cards
{
  "type": "virtual",
  "currency": "EUR",
  "limit": 5000,
  "user_id": "12345"
}
```

### Example: Set Spending Controls

```json
PATCH /api/v1/cards/12345
{
  "spend_limit": 3000,
  "allowed_merchants": ["Google Ads", "AWS", "HubSpot"]
}
```

**Note:** These are from Wallester's blog examples. Actual endpoint paths and field names may differ — full spec is in the API docs portal.

### SDKs

| Language | Status |
|---|---|
| TypeScript | Available (via Konfig) |
| Python | Coming soon |
| Java | Coming soon |

### Webhooks
Real-time notifications for:
- Payment approvals and declines
- Card status changes
- KYC verification results
- Balance changes

---

## 5. Card Controls — MCC Restriction Capabilities

This is the critical feature for Leo's construction materials use case.

### What Wallester Offers
- **Dynamic spending limits** — per card, per user, adjustable via API
- **Merchant whitelists** — allow only specific merchants
- **Merchant restrictions** — block by merchant type/category
- **Usage type controls** — single-use (disposable) or multi-use cards
- **Transaction type limits** — separate limits for contactless, online, POS, ATM
- **Real-time card management** — freeze, unfreeze, cancel instantly

### MCC Code for Construction Materials
The relevant Merchant Category Code is **MCC 5039** — "Construction Materials, Not Elsewhere Classified." This covers:
- General building supply stores
- Lumber yards
- Roofing material suppliers
- Home improvement retailers

Adjacent MCCs that may be relevant:
- **5211** — Lumber and Building Materials Stores
- **5231** — Glass, Paint, and Wallpaper Stores
- **5251** — Hardware Stores
- **5200** — Home Supply Warehouse Stores

### How MCC Filtering Would Work
1. Issue a virtual card tied to a specific renovation project
2. Set `allowed_merchants` to MCC codes 5039, 5211, 5231, 5251, 5200
3. Set a spending limit matching the materials budget from the scope
4. Card can only be used at construction materials merchants, up to the agreed budget
5. Real-time transaction data flows back to Leo for milestone tracking

### Comparison: MCC Controls Across Providers

| Feature | Wallester | Stripe Issuing | Wise Platform |
|---|---|---|---|
| MCC allow/block lists | Yes (merchant whitelists) | Yes (spending_controls) | Yes (authorization rules) |
| Per-card limits | Yes | Yes | Yes |
| Real-time webhooks | Yes | Yes | Yes |
| EU coverage | EEA + UK | Limited EU (mainly US/UK) | EU + global |
| Licensed issuer | Yes (own EMI) | Via banking partners | Via banking partners |
| White-label | Full | Limited | No |

---

## 6. Geographic Coverage

### Supported Markets

| Region | Status |
|---|---|
| **European Economic Area (30 countries)** | Full support |
| **Spain** | Supported (EEA member) |
| **United Kingdom** | Supported |
| **United Arab Emirates** | Supported |
| **Singapore** | Supported |
| **USA** | Supported |
| **Canada** | Supported |

### Supported Currencies
EUR, USD, GBP, SEK, NOK, DKK, PLN, CZK, HUF, RON

Payments can be made in **any currency** — automatic conversion at Visa rate + 2%.

### Spain-Specific Notes
- Spain is an EEA member — fully within Wallester's licensed territory
- EUR is the base currency — no FX needed for domestic transactions
- SEPA bank transfers for account top-up — free
- Physical cards deliverable to Spain
- Leo Scope's Spanish tradespeople and homeowners could hold Wallester-issued cards

---

## 7. Onboarding Process

### For Business (Self-Serve) Clients
1. **Sign up** on wallester.com
2. **Company data verification** (KYB)
3. **Sign program participation agreement**
4. **Full platform access** — within 24 hours
5. **Dedicated manager** assigned

### For White-Label (Embedded Finance) Partners
Wallester's 4-phase launch protocol:

| Phase | Duration | Activities |
|---|---|---|
| **1. Commercial Kick-off** | Week 1-2 | LOI, subscription tier selection, commercial terms |
| **2. Compliance & Due Diligence** | Week 2-4 | KYB checks, card type definition, Master Agreement |
| **3. Technical Implementation** | Week 4-8 | API integration, Visa Co-brand approval, dedicated BIN, 3D Secure setup |
| **4. Go-Live & Operations** | Week 8+ | Public issuance, settlement management, tokenization |

**Timeline:** 4-8 weeks typical for white-label launch. Industry average is 3-4 months. Wallester claims some launches in "a few weeks."

---

## 8. How Cards Are Issued to End Users

### Virtual Cards
1. Platform calls `POST /api/v1/cards` with user details and card parameters
2. Card is **instantly activated** — PAN, expiry, CVV returned
3. Card can be immediately added to **Apple Pay, Google Pay, Samsung Pay** via tokenization
4. User can make online purchases immediately

### Physical Cards
1. Platform calls API to order physical card with custom branding
2. Card manufactured and shipped to user's address
3. **Standard delivery:** ~€5, estimated 5-7 business days
4. **Express delivery:** ~€20, faster shipping
5. Card activated via API or dashboard once received

### Cardholder KYC
For white-label programs, KYC can be handled:
- **By Wallester** — built-in automated KYC system (identity docs, biometric, residence verification)
- **By the platform** — bring your own KYC and pass verified user data to Wallester

---

## 9. Compliance Requirements

### Wallester Handles (as licensed EMI)
- **PCI DSS** compliance for card data security
- **PSD2** compliance for payment services
- **GDPR** for data protection
- **AML/CFT** monitoring and reporting
- **3D Secure 2.0** for online transaction authentication
- **Visa scheme compliance** — as Principal Member
- **Safeguarding** — client funds segregated per EMI regulations
- **Transaction monitoring** — fraud detection

### Platform Partner Must Handle
- **User onboarding UX** — collecting KYC data from end users
- **Product compliance** — ensuring your use case fits Wallester's acceptable use policy
- **Data processing agreement** — GDPR DPA with Wallester
- **Industry risk fee** — some industries incur additional compliance costs
- **Ongoing reporting** — depending on your regulatory status

### What Leo Would NOT Need
- Banking license
- EMI license
- Direct Visa membership
- PCI DSS certification (Wallester handles card data)
- AML officer (Wallester handles AML)

---

## 10. SDKs & Integration Options

| Integration Method | Details |
|---|---|
| **REST API** | Primary integration path. JSON over HTTPS. |
| **TypeScript SDK** | Available via Konfig |
| **Python SDK** | Coming soon |
| **Java SDK** | Coming soon |
| **GitHub Examples** | github.com/wallester/integration-examples |
| **Sandbox** | Full private testing environment |
| **Webhooks** | Event-driven notifications |
| **Dashboard** | Manual card management (Client Portal) |
| **Mobile App** | Wallester app for cardholder self-service |

---

## 11. Competitive Positioning

| Dimension | Wallester | Stripe Issuing | Marqeta |
|---|---|---|---|
| **License** | Own EMI (Estonia) | Partners with banks | Partners with banks |
| **EU coverage** | EEA + UK (30+ countries) | Limited EU | Limited EU |
| **Spain** | Yes | Check availability | Check availability |
| **White-label** | Full (dedicated BIN, branding) | Limited branding | Full |
| **Free tier** | 300 cards free | No free tier | No free tier |
| **MCC controls** | Yes | Yes (granular) | Yes (JIT funding) |
| **Integration time** | ~1 day (business), 4-8 weeks (WL) | Weeks-months | Months |
| **Tokenization** | Apple/Google/Samsung Pay | Apple/Google Pay | Apple/Google Pay |
| **KYC built-in** | Yes | No (BYO) | No (BYO) |
| **Target market** | EU-first, SMB + enterprise | US-first, expanding | US-first, enterprise |
| **Pricing transparency** | Published plans | Published (higher) | Custom only |

### Key Wallester Advantages for Leo
1. **EU-native** — licensed in Estonia, designed for EEA. Spain is first-class.
2. **Free tier** — 300 virtual cards at €0/month is enough for early testing
3. **Fast launch** — Business tier in 24 hours, white-label in weeks
4. **BIN sponsorship** — Leo doesn't need Visa membership
5. **Built-in KYC/AML** — no separate identity verification vendor needed
6. **EUR-native** — no FX costs for Spanish transactions

### Key Risks / Concerns
1. **MCC filtering granularity** — need to verify exact API support for MCC allow-lists (marketing pages mention "merchant whitelists" but not specifically MCC codes)
2. **White-label pricing opacity** — custom negotiation required, no published rates
3. **Customer support** — rated 7.1/10 on OMR Reviews, lowest of their scores
4. **SDK maturity** — only TypeScript available, Python/Java "coming soon"
5. **No credit cards** — Wallester issues debit/prepaid only. Credit card programs may be possible under white-label but not standard.
6. **Settlement timing** — need to understand fund flow timing for escrow use cases

---

## 12. Relevance to Leo Scope

### Potential Use Cases

#### A. Materials-Only Project Cards
Issue a virtual card per renovation project, restricted to construction materials MCCs (5039, 5211, 5231, 5251). Homeowner funds the card via SEPA or card top-up. Tradesperson uses the card at Leroy Merlin, Bricomart, etc. Leo gets real-time transaction data for reconciliation against the scope.

**Value:** Eliminates materials advance disputes. Homeowner knows money went to materials. Tradesperson doesn't front cash.

#### B. Milestone-Released Payment Cards
Issue a virtual card for each milestone. When homeowner approves a milestone, Leo funds the card up to the milestone amount. Tradesperson withdraws or spends.

**Value:** Replaces bank transfer delays with instant card funding. More control than wire transfers.

#### C. Escrow + Card Hybrid
Homeowner deposits to Leo escrow (Stripe). Leo issues Wallester virtual card to tradesperson. On milestone approval, Leo tops up the Wallester card from escrow funds. Card restricted to materials MCCs for materials milestones, unrestricted for labor milestones.

**Value:** Combines Stripe's escrow with Wallester's card controls for maximum trust.

#### D. Tradesperson Expense Management
Free tier: tradesperson signs up to Leo, gets virtual cards for business expenses. Receipts auto-matched to projects. Premium feature ladder.

**Value:** Acquisition wedge — tradesperson gets free card → uses Leo for scope → Leo captures transaction data.

### Integration Complexity Estimate

| Step | Effort | Dependencies |
|---|---|---|
| Sign up for Business tier | 1 hour | Company registration docs |
| API sandbox testing | 1-2 days | API key |
| Basic card issuance (virtual) | 1 day | Working API integration |
| MCC restriction testing | 1-2 days | Confirm API supports MCC filtering |
| Webhook → Supabase pipeline | 2-3 days | Backend work |
| White-label application | 4-8 weeks | Commercial negotiation |
| Full production integration | 2-4 weeks | After WL approval |

### Recommended Next Steps
1. **Sign up for Business free tier** — test the API, confirm MCC filtering capabilities
2. **Read full API docs** at api-doc.wallester.com — verify exact endpoint structure
3. **Test virtual card creation** in sandbox — confirm EUR cards work, test spending controls
4. **Contact Wallester sales** — ask specifically about MCC allow-lists and white-label pricing for a construction/renovation platform
5. **Evaluate against Stripe Issuing** — Stripe is already integrated for payments; adding Issuing may be simpler operationally

---

## Sources

- https://wallester.com/api — Developer Portal
- https://wallester.com/business/api-solutions — Business API page
- https://wallester.com/business/pricing/price-list — Published pricing
- https://wallester.com/card-payment-platform/bin-sponsorship — BIN sponsorship details
- https://wallester.com/card-payment-platform/card-issuing — Card issuing platform
- https://wallester.com/services/kyc-aml — KYC/AML system
- https://wallester.com/faq — FAQ
- https://wallester.com/blog/business-insights/from-erp-to-fintech-how-to-add-visa-card-issuing-in-just-a-few-api-calls — Technical integration guide
- https://api-doc.wallester.com/ — API documentation portal
- https://github.com/wallester/integration-examples — Code examples
- https://konfigthis.com/sdk/wallester/ — SDK availability
- https://omr.com/en/reviews/product/wallester — OMR Reviews 2026
- https://payatlas.com/mcc-codes/5039-construction-materials — MCC 5039 reference
- https://stripe.com/docs/issuing/categories — Stripe MCC reference (comparison)

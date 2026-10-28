# Native App Development — Framework & Submission Exploration

**Last updated:** 2026-04-02
**Current state:** Capacitor scaffolding exists (no native projects generated)
**Recommendation:** Migrate to React Native + Expo
**Realistic timeline to both app stores:** ~4-5 weeks (Apple in under a week, Google bottlenecked by 14-day testing gate)
**Spain mobile market:** 71% Android, 29% iOS (tradespeople skew even more Android)
**App store accounts needed:** Apple Developer ($99/year), Google Play ($25 one-time)

---

## Table of Contents

- [1. Current Capacitor State](#1-current-capacitor-state)
- [2. Framework Comparison](#2-framework-comparison)
- [3. Why Expo / React Native Wins](#3-why-expo--react-native-wins)
- [4. Migration from Capacitor to Expo](#4-migration-from-capacitor-to-expo)
- [5. App Store Submission — Apple](#5-app-store-submission--apple)
- [6. App Store Submission — Google Play](#6-app-store-submission--google-play)
- [7. Stripe on Native](#7-stripe-on-native)
- [8. Biometric Authentication](#8-biometric-authentication)
- [9. Deep Linking](#9-deep-linking)
- [10. Over-the-Air Updates](#10-over-the-air-updates)
- [11. What YC / Solo Founders Are Using](#11-what-yc--solo-founders-are-using)
- [12. Development Workflow (Vibe Coding Friendly)](#12-development-workflow-vibe-coding-friendly)
- [13. Realistic Timeline](#13-realistic-timeline)
- [14. Cost Breakdown](#14-cost-breakdown)

---

## 1. Current Capacitor State

The `scope-app/apps/mobile/` directory has a **minimal Capacitor scaffold** that has never been used:

| Item | Status | Issue |
|------|--------|-------|
| `capacitor.config.ts` | Exists | `webDir: '../web/dist'` doesn't match Vite output (`../../public/app`) |
| `package.json` | Exists | Version mismatch: `@capacitor/core` ^8.2.0 vs `@capacitor/cli` ^7.6.0 |
| `android/` directory | **Missing** | `npx cap add android` never run |
| `ios/` directory | **Missing** | `npx cap add ios` never run |
| Native plugins | None | No camera, biometric, deep link, push notification plugins |
| Capacitor plugins | None | Zero `@capacitor/*` plugins beyond core |

**Assessment:** This is a scaffold, not an integration. No native projects, no native plugins, no builds ever attempted. Starting fresh with Expo loses nothing.

---

## 2. Framework Comparison

### Capacitor (current)

| Aspect | Details |
|--------|---------|
| **Architecture** | WebView wrapper — your web app runs in a WebView, native features via plugins |
| **UI** | Your existing React + Tailwind CSS renders in a WebView |
| **Performance** | Web-speed (JS thread for everything, no native rendering) |
| **Native APIs** | Via plugins — must install each one separately |
| **Stripe** | `@capacitor-community/stripe` (community plugin, not official) |
| **Biometrics** | `@nickreardon/capacitor-native-biometric` (community, 60 GitHub stars) |
| **Developer experience** | Familiar web dev, but debugging native issues requires Xcode/Android Studio |
| **AI/vibe coding** | OK — it's just React, but native integration code has less community knowledge |
| **App Store risk** | Apple has increasingly rejected WebView-wrapped apps that don't use native UI |

### React Native + Expo (recommended)

| Aspect | Details |
|--------|---------|
| **Architecture** | Native rendering — React components compile to actual native views |
| **UI** | React Native components (`View`, `Text`, `TouchableOpacity`) — not HTML |
| **Performance** | Near-native (New Architecture + Fabric renderer in React Native 0.76+) |
| **Native APIs** | First-class SDK access — camera, biometrics, push, etc. |
| **Stripe** | `@stripe/stripe-react-native` — official, 281K weekly downloads |
| **Biometrics** | `expo-local-authentication` — official Expo module, Face ID + Touch ID + fingerprint |
| **Developer experience** | TypeScript, hot reload, Expo Go for instant preview, EAS for cloud builds |
| **AI/vibe coding** | Excellent — largest React Native community, most LLM training data, copilot-friendly |
| **App Store risk** | Native rendering = no WebView rejection risk |

### Flutter (alternative)

| Aspect | Details |
|--------|---------|
| **Architecture** | Custom rendering engine (Skia) — draws every pixel itself |
| **Language** | Dart (not TypeScript) — would require learning new language |
| **UI** | Dart widgets — can't reuse any React knowledge or components |
| **Stripe** | `flutter_stripe` — good but smaller community than React Native |
| **AI/vibe coding** | Worse — less Dart in training data, fewer Stack Overflow answers |
| **Verdict** | Not recommended — learning Dart is a tax for a solo non-coder founder |

---

## 3. Why Expo / React Native Wins

### For Leo specifically

1. **TypeScript stays** — all business logic, API clients, type definitions transfer
2. **React mental model stays** — components, hooks, state, effects — same paradigm
3. **Stripe is first-class** — official SDK, PCI-compliant, Apple Pay + Google Pay, 3D Secure
4. **Biometrics are first-class** — `expo-local-authentication` wraps native APIs directly
5. **Deep linking is automatic** — Expo Router: every route is a deep link by default
6. **OTA updates** — EAS Update pushes JS changes without app store review (for non-native changes)
7. **Cloud builds** — EAS Build compiles iOS without a Mac (runs on Expo's cloud)
8. **Vibe coding / AI friendly** — React Native has the largest community, most documentation, most copilot training data

### What the community says (2026 consensus)

Reddit (`r/reactnative`, `r/ExpoDevs`, `r/startups`), YC forums, and Indie Hackers converge on:
- **Expo is the default for new React Native projects** — even large companies (Coinbase, Shopify, Bloomberg) use it
- **Capacitor is fine for content apps** but fintech/identity apps need native (biometrics, Stripe SDK, secure storage)
- **Flutter is loved by Flutter devs** but React devs should stick with React Native — the context switch isn't worth it
- **Solo founders overwhelmingly choose Expo** because of EAS Build (no Xcode), OTA updates, and the TypeScript ecosystem

---

## 4. Migration from Capacitor to Expo

### What transfers directly

| Asset | Reuse? | Notes |
|-------|--------|-------|
| TypeScript types (`BriefUpdate`, `ProfileUpdate`, etc.) | 100% | Same `.ts` files |
| API client (`lib/api.ts`) | 100% | HTTP calls are platform-agnostic |
| Business logic (hooks, state management) | 95% | Minor adjustments for navigation |
| `@scope/ui` components | 0% | Must be rewritten as React Native components |
| Tailwind CSS classes | 0% | React Native uses StyleSheet or NativeWind |
| HTML-based landing pages | N/A | Stay as web pages, not in the app |

### What needs rewriting

| Component | Web (current) | React Native equivalent |
|-----------|--------------|----------------------|
| `<div>` | HTML div | `<View>` |
| `<span>` / `<p>` | HTML text | `<Text>` |
| `<input>` | HTML input | `<TextInput>` |
| `<button>` | HTML button | `<TouchableOpacity>` or `<Pressable>` |
| CSS classes | Tailwind | StyleSheet / NativeWind |
| Router | React Router | Expo Router (file-based) |
| Local storage | `localStorage` | `AsyncStorage` / `expo-secure-store` |

### NativeWind (Tailwind for React Native)

NativeWind lets you use Tailwind class names in React Native. It compiles Tailwind classes to StyleSheet objects at build time:

```tsx
import { View, Text } from 'react-native'

export const ProfileCard = () => (
  <View className="bg-stone-900 rounded-2xl p-6">
    <Text className="text-amber-100 font-serif text-xl">Carlos Ruiz</Text>
    <Text className="text-stone-400 mt-1">Plumber · Barcelona</Text>
  </View>
)
```

This significantly reduces the migration effort — Leo's Tailwind class names can be reused almost verbatim.

### Recommended migration approach

1. **Create Expo project alongside Capacitor** — `npx create-expo-app scope-mobile` in `scope-app/apps/`
2. **Copy TypeScript types and API client** — verbatim
3. **Rewrite UI components** with NativeWind — same class names, different JSX elements
4. **Start with one screen** (onboarding) → get it on TestFlight/Play Internal Testing
5. **Iterate** — add screens one at a time
6. **Delete Capacitor scaffold** when Expo is working

---

## 5. App Store Submission — Apple

### Requirements

| Requirement | Status |
|------------|--------|
| Apple Developer account ($99/year) | **Need to create** |
| Mac for signing (or EAS Build) | EAS Build handles this in the cloud |
| App name | "Leo Scope" or "Scope by Leo" |
| Bundle ID | `casa.scope.app` (matches Capacitor config) |
| App icon (1024x1024) | Need to create |
| Screenshots (6.7", 6.5", 5.5" iPhones + iPads) | Need to create |
| Privacy policy URL | `leo.casa/privacy` (exists) |
| App Review information | Test account details, demo video |

### Review process

| Step | Duration | Notes |
|------|---------|-------|
| Submit build via EAS | ~15 min build time | Cloud build, no Mac needed |
| Automatic checks | Minutes | Binary analysis, metadata validation |
| In-queue for review | 0-24 hours | Depends on volume |
| Human review | **24-48 hours typical** | Straightforward apps clear fast |
| **Typical first submission** | **2-3 days** | Most clean apps pass first try |

Apple's review is fast for apps that use native rendering (Expo), have real functionality (biometrics, payments), and don't violate guidelines. The 7-14 day horror stories come from apps that get flagged for WebView wrapping, minimum functionality, or policy violations.

### Common rejection reasons (avoid these and you're fine)

| Reason | How to avoid |
|--------|-------------|
| **4.2 — Minimum Functionality** | Include native features (biometrics, camera, push). Don't ship a glorified website. |
| **2.1 — App Completeness** | All features must work. No placeholder screens, no "coming soon" |
| **5.1.1 — Data Collection** | Privacy policy must match actual data collection |
| **WebView wrapper** | Use Expo with native rendering — not Capacitor |

### Does the first version need to be perfect?

**No.** It needs to not crash, have real functionality, and comply with guidelines. Many companies ship a minimal v1 and iterate via updates. The goal is to clear the gate once — after that, updates review in ~24 hours.

---

## 6. App Store Submission — Google Play

### Requirements

| Requirement | Status |
|------------|--------|
| Google Play Developer account ($25 one-time) | **Need to create** |
| AAB (Android App Bundle) | EAS Build generates this |
| App icon (512x512) | Need to create |
| Feature graphic (1024x500) | Need to create |
| Screenshots (phone + 7" tablet + 10" tablet) | Need to create |
| Privacy policy URL | `leo.casa/privacy` (exists) |
| Content rating questionnaire | Fill out in Play Console |

### The 14-day closed testing gate (real but manageable)

Since November 2023, Google requires **all new personal developer accounts** to go through closed testing before production release:

| Step | Duration | Details |
|------|---------|---------|
| **1. Create closed testing track** | 1 day | Upload AAB, set up Google Group for testers |
| **2. Recruit 12+ testers** | 1-3 days | Friends, family, or tester services (see below) |
| **3. Run closed test for 14 continuous days** | **14 days (mandatory)** | Clock starts when 12 testers opt in |
| **4. Apply for production access** | Same day | Button appears after closed test passes |
| **5. Production review** | 1-3 days | Usually fast after closed testing |

**Total: ~3 weeks.** The 14-day gate cannot be shortened, but it's a calendar wait — not a technical blocker.

### How companies actually handle the 12 testers

This is not the obstacle it sounds like. Cheapest and best options:

| Option | Cost | How it works |
|--------|------|-------------|
| **PrimeTestLab** ([primetestlab.com](https://primetestlab.com/)) | **$14.99** | 12+ real testers, start within 4-6 hours, 99.8% success rate, money-back guarantee |
| **Testers Community** ([testerscommunity.com](https://www.testerscommunity.com/)) | **$15** | 25 professional testers, daily engagement, money-back guarantee |
| **12testers14days.com** | **$10/tester** (gap-fill option) | Pay only for testers you need, 60% discount promos |
| **Friends and family** | Free | 12 people with Android phones opt in via a Google Group link |
| **Reddit r/androidapps** | Free | People actively offer to test new apps |

**Recommendation:** Pay $15 at PrimeTestLab or Testers Community. It's not worth the hassle of coordinating 12 friends when a service does it for the price of a coffee. They start within hours, guarantee daily engagement, and have 99%+ success rates.

Google tracks real engagement (device IDs, IP diversity, actual app usage), so fake accounts won't work. These services use real humans on real devices.

### Tips for faster Google review

- Fill out the data safety form completely and accurately
- Use the pre-launch report (automated testing) to catch issues before review
- Keep the first version simple — add features via updates
- Target API level 34+ (Android 14) — Google requires it

---

## 7. Stripe on Native

### `@stripe/stripe-react-native` SDK

The official Stripe React Native SDK is the best mobile payment integration available:

| Feature | Support |
|---------|---------|
| **PaymentSheet** | Pre-built UI for card entry, Apple Pay, Google Pay |
| **Apple Pay** | Full — via Merchant ID configuration |
| **Google Pay** | Full — via configuration |
| **3D Secure / SCA** | Automatic for EU (mandatory in Spain under PSD2) |
| **Card scanning** | iOS + Android camera |
| **Setup Intents** | Save card for future payments |
| **SEPA Direct Debit** | Supported in PaymentSheet |
| **PCI compliance** | Card data goes directly to Stripe — never touches our server |
| **Weekly downloads** | 281K (March 2026) |

### Integration pattern

```tsx
import { StripeProvider, usePaymentSheet } from '@stripe/stripe-react-native'

const App = () => (
  <StripeProvider
    publishableKey="pk_live_..."
    merchantIdentifier="merchant.casa.scope.app"
  >
    <PaymentScreen />
  </StripeProvider>
)

const PaymentScreen = () => {
  const { initPaymentSheet, presentPaymentSheet } = usePaymentSheet()

  const handlePay = async () => {
    // Backend creates PaymentIntent and returns client secret
    const { clientSecret } = await api.createPaymentIntent(amount)
    
    await initPaymentSheet({
      paymentIntentClientSecret: clientSecret,
      merchantDisplayName: 'Leo Scope',
      applePay: { merchantCountryCode: 'ES' },
      googlePay: { merchantCountryCode: 'ES', testEnv: false },
    })
    
    const { error } = await presentPaymentSheet()
    if (!error) {
      // Payment succeeded
    }
  }
}
```

### Stripe Connect on native

For marketplace payments (contractor payouts), the flow is:
1. Backend creates PaymentIntent with `transfer_group` and `on_behalf_of`
2. Mobile app presents PaymentSheet
3. Homeowner pays
4. Backend handles transfer to contractor's Connected Account

The mobile app never needs to know about Connect — it just presents the PaymentSheet.

---

## 8. Biometric Authentication

### `expo-local-authentication`

Official Expo module for biometric auth. Wraps native APIs directly (not WebView bridge):

| Feature | iOS | Android |
|---------|-----|---------|
| Face ID | Yes | N/A |
| Touch ID | Yes | N/A |
| Fingerprint | N/A | Yes |
| Iris scan | N/A | Yes (Samsung) |
| Device PIN fallback | Configurable | Configurable |

### Implementation

```tsx
import * as LocalAuthentication from 'expo-local-authentication'

const authenticateUser = async () => {
  const hasHardware = await LocalAuthentication.hasHardwareAsync()
  const isEnrolled = await LocalAuthentication.isEnrolledAsync()
  
  if (!hasHardware || !isEnrolled) {
    // Fallback to phone OTP
    return signInWithPhoneOTP()
  }
  
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Unlock Leo Scope',
    cancelLabel: 'Use phone number',
    disableDeviceFallback: false, // allow device PIN
  })
  
  if (result.success) {
    // Load Supabase session from SecureStore
    const session = await SecureStore.getItemAsync('supabase_session')
    // Auto-sign in
  }
}
```

### Security pattern

Biometrics should protect **session access**, not replace authentication:

1. **First login:** Phone OTP via Supabase Auth → session stored in `expo-secure-store` (hardware-backed keychain)
2. **Subsequent opens:** Biometric prompt → if passed, load session from secure store
3. **Session expired:** Biometric + automatic refresh token usage
4. **New device:** Phone OTP required again (no biometric transfer)

---

## 9. Deep Linking

### Expo Router (file-based routing)

With Expo Router, every route is automatically a deep link:

```
app/
  (tabs)/
    index.tsx          → leoscope://
    jobs.tsx           → leoscope://jobs
    profile.tsx        → leoscope://profile
  job/
    [id].tsx           → leoscope://job/abc123
  canvas/
    [token].tsx        → leoscope://canvas/LCS-4821
  auth/
    callback.tsx       → leoscope://auth/callback
```

### Universal Links (iOS) + App Links (Android)

For `https://leo.casa/scope/LCS-4821` to open the app instead of the browser:

**iOS (`apple-app-site-association`):**
```json
{
  "applinks": {
    "apps": [],
    "details": [{
      "appID": "TEAM_ID.casa.scope.app",
      "paths": ["/scope/*", "/canvas/*", "/job/*"]
    }]
  }
}
```

**Android (`assetlinks.json`):**
```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "casa.scope.app",
    "sha256_cert_fingerprints": ["..."]
  }
}]
```

Both files hosted at `leo.casa/.well-known/`.

### WhatsApp → App flow

The ideal contractor onboarding:

```
Leo sends WhatsApp message with link: "https://leo.casa/scope/LCS-4821"
  → If app installed: opens directly in app at the scope screen
  → If not installed: opens in mobile browser
    → Banner: "Open in Leo Scope" (Smart App Banner / Instant App)
    → User installs → on first open, deferred deep link takes them to the scope
```

Expo's `expo-linking` handles both cases. For deferred deep links (link clicked before install), services like Branch.io or Expo's built-in linking handle the redirect.

---

## 10. Over-the-Air Updates

### EAS Update

The killer feature of Expo for iteration speed: push JavaScript/TypeScript changes without going through app store review.

| What | Details |
|------|---------|
| **What can be updated OTA** | JS/TS code, assets (images, fonts), configuration |
| **What requires a new build** | Native module changes, new Expo SDK version, new permissions |
| **Delivery** | CDN-backed, users get update on next app open |
| **Rollback** | Instant — point back to previous update |
| **Cost** | Free tier: 1,000 monthly active users. $99/month: 50,000 MAUs |

This means: once the app is on both stores, most changes (UI tweaks, bug fixes, new screens, copy changes) ship in minutes, not days/weeks.

---

## 11. What YC / Solo Founders Are Using

### 2026 consensus from research

| Source | Recommendation |
|--------|---------------|
| YC batch companies (W26, S25) | React Native + Expo dominant for mobile-first startups |
| `r/reactnative` (2026) | "Expo is now the default" — direct quote from top posts |
| `r/ExpoDevs` | Active community, 50K+ members, most questions answered within hours |
| Indie Hackers | Solo founders report going from zero to App Store in 2-4 weeks with Expo |
| Vercel/Next.js community | Many pairing Next.js web + Expo mobile (shared TypeScript) |
| AI/vibe coders | React Native has the most LLM training data → best copilot suggestions |
| Coinbase, Shopify, Discord | All use React Native / Expo in production |

### Specific tools solo founders combine with Expo

| Tool | Purpose |
|------|---------|
| **NativeWind** | Tailwind CSS for React Native (reuse class names) |
| **Expo Router** | File-based routing (like Next.js) |
| **EAS Build** | Cloud builds (no Mac needed for iOS) |
| **EAS Update** | OTA updates (skip app store for JS changes) |
| **Supabase** | Auth + database + realtime |
| **Stripe React Native** | Payments |
| **Sentry** | Error tracking |

---

## 12. Development Workflow (Vibe Coding Friendly)

### Getting started (from zero to running app)

```bash
# Create Expo project
npx create-expo-app scope-mobile --template tabs
cd scope-mobile

# Install key dependencies
npx expo install @stripe/stripe-react-native
npx expo install expo-local-authentication
npx expo install @supabase/supabase-js
npx expo install @react-native-async-storage/async-storage
npx expo install nativewind tailwindcss

# Run in Expo Go (instant preview on phone)
npx expo start
# Scan QR code with phone camera → app runs instantly
```

### Daily development loop

1. Write code in Cursor (TypeScript, React Native components)
2. Hot reload on physical device via Expo Go (changes appear in < 1 second)
3. For native features (biometrics, Apple Pay): use development build via EAS
4. AI copilot works perfectly — React Native patterns are well-represented in training data

### Building for submission

```bash
# iOS (builds in Expo's cloud — no Mac needed)
eas build --platform ios --profile production

# Android
eas build --platform android --profile production

# Submit to stores
eas submit --platform ios
eas submit --platform android
```

### Why this is "vibe coding friendly"

- **No Xcode required** for most development (EAS Build handles it)
- **No Android Studio required** for most development
- **TypeScript + React** — the most copilot-supported stack
- **Hot reload** — see changes instantly on physical device
- **Expo SDK** handles native complexity — camera, biometrics, push, etc. are one-line installs
- **File-based routing** — creating a new screen = creating a new file

---

## 13. Realistic Timeline

### Spain market context

**Spain is 71% Android, 29% iOS** (StatCounter, February 2026). Tradespeople skew even more Android (mid-price phones dominate in the trades). Both stores matter, but Google Play reaches more of your target users.

### The plan: submit to both simultaneously

| Time | Milestone |
|------|-----------|
| Week 1-2 | Build app (core screens, Stripe, biometrics, deep links) |
| End of Week 2 | Submit to Apple App Store + start Google closed testing (recruit 12 testers, start 14-day clock) |
| **Day 2-3 after Apple submit** | **Apple approves → you're on the App Store** |
| Week 4 (14 days after testers opt in) | Google closed testing completes → submit for production |
| Week 4-5 | **Google approves → you're on Play Store** |

### Summary

| Store | Time from submit to live | Bottleneck |
|-------|-------------------------|------------|
| **Apple App Store** | 2-3 days | Review (usually fast for clean apps) |
| **Google Play Store** | ~3 weeks | 14-day mandatory closed testing gate |
| **Both stores** | **~4-5 weeks total** | Google's calendar gate |

### Does the first version need to be perfect?

No. Ship the minimum that works: onboarding (phone OTP), a couple of core screens (profile, jobs), biometric unlock, and Stripe payment. Iterate via updates (24h review for updates on both stores, or instant via Expo OTA for JS-only changes).

---

## 14. Cost Breakdown

| Item | Cost | Frequency |
|------|------|-----------|
| Apple Developer account | $99 | Annual |
| Google Play Developer account | $25 | One-time |
| EAS Build (free tier) | $0 | 30 builds/month |
| EAS Build (production) | $99/month | Unlimited builds, 50K OTA MAUs |
| EAS Submit | Free | Included with build |
| Expo Go (development) | Free | Unlimited |
| **Total to get started** | **$124** | One-time |
| **Total ongoing (production)** | **$99-198/month** | EAS + Apple Developer |

## 15. Interim Strategy: WhatsApp as Push Notifications

Until the native app is on both stores, WhatsApp replaces push notifications entirely. This already works — Leo's backend sends WhatsApp messages via Meta Cloud API.

### What WhatsApp handles before the app exists

| Native app feature | WhatsApp interim equivalent |
|-------------------|---------------------------|
| Push notification: "New message from homeowner" | WhatsApp message with link to web app |
| Push notification: "Milestone approved" | WhatsApp message with payment details |
| Push notification: "New job match" | WhatsApp message with job brief link |
| Deep link into app | One-time link to web app (`leo.casa/scope/LCS-4821`) |
| Biometric login | Phone number already verified by WhatsApp |

### Why this works well for Leo

- **Tradespeople already live in WhatsApp** — it's the default communication tool for Spanish trades
- **WhatsApp messages have higher open rates than push notifications** (~98% vs ~50%)
- **No app download friction** — users click a link and they're in the web app
- **Already built** — `backend/routes/meta_whatsapp.py` handles sending, templates are configured

### When to switch to native push

Once the app is on both stores and has meaningful adoption (100+ users), add push notifications as a **supplement** to WhatsApp, not a replacement. Many users will prefer WhatsApp notifications even after installing the app.

---

## Related Documents

| Document | What it covers |
|----------|---------------|
| `scope-app/apps/mobile/` | Current Capacitor scaffold (to be replaced) |
| `scope-app/apps/web/` | React web app (business logic transfers to Expo) |
| `internal/service-integrations/stripe/README.md` | Stripe native SDK details |
| `internal/service-integrations/supabase-auth/README.md` | Auth + React Native integration |
| `scope-app/packages/ui/` | Shared components (need rewrite for React Native) |

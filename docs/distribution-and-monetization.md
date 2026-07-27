# Distribution & Monetization Guide

How to get this app onto phones: from a quick dev preview, to a free friends beta,
to a paid public launch on both stores. Written to be a standalone reference so
you do not have to reconstruct it later.

Last updated: 2026-07-27.

---

## 0. What this app is (the facts that drive everything below)

- **Expo managed workflow**, Expo SDK ~57, React Native 0.86. One codebase builds
  for **both iOS and Android**. Nothing is Android-only.
- App config lives in `mobile/app.json`. Build config lives in `mobile/eas.json`.
- Identifiers (set 2026-07-27):
  - iOS `bundleIdentifier`: `com.agentiwise.productivity`
  - Android `package`: `com.agentiwise.productivity`
  - URL scheme: `productivityapp` (this is what lets the OAuth callback
    `productivityapp://composio-callback` return into the app on a real device).
- Backend: FastAPI on EC2, reachable at `https://52-64-67-235.sslip.io`. The app
  points here via `EXPO_PUBLIC_API_URL`. Native apps are not subject to CORS, so
  device builds talk to it fine. (The backend `CORS_ORIGINS` list only matters for
  the web preview.)
- Auth mode: `own` (our own email + OTP + password), set via `EXPO_PUBLIC_AUTH_MODE=own`.
- **EAS builds do NOT read `mobile/.env`.** Env vars for builds are baked into
  `eas.json` (already done) or set as EAS secrets.

There are three stages. Do them in order; each unlocks the next.

---

## 0.5. Accounts: personal vs organization (decide this first)

Researched against official expo.dev / Apple / Google docs, current 2026.

**Expo:** create an **Organization** for commercial/client work; keep hobby projects
on your personal account. One login can own a personal account and belong to orgs at
once. Start commercial work as an org from day one: Expo documents converting a
personal account to an org and changing an org owner, but there is **no clean
per-project transfer between two existing accounts**, so starting as an org avoids a
migration. Name it after the company (e.g. `agentiwise`).

- **Commercial use is allowed on the Free tier.** Expo's terms only forbid reselling
  EAS itself, not shipping paid apps. "Personal account" is an account-type label,
  not a license limit.
- **Free tier quotas:** 15 Android + 15 iOS builds/month, 1 concurrent build,
  low-priority queue, 45-min build timeout, 1,000 EAS Update MAU. Paid tiers:
  Starter $19/mo, Production $199/mo, Enterprise custom. Pay only when you exceed
  build count, need concurrency/faster queue, or pass 1,000 update users.
- Project ownership is the `owner` field under `expo` in `app.json`. Set it to the
  org. Run `eas init` while the org is selected.

**Store accounts (this is where "commercial" really matters):** both stores cost the
same regardless of type (**Apple $99/yr**, **Google $25 one-time**), but the type
sets the seller name shown to users:
- **Individual:** your personal legal name is shown. No paperwork.
- **Organization/Company:** business name is shown, but requires a free **D-U-N-S
  number** (takes a few days), a business website + email, and (Apple) someone with
  authority to enroll. Only org accounts allow multiple team members with roles.

For a real product under Agentiwise: enroll both stores as **Organization**, and
**request the D-U-N-S early** since it gates enrollment and is slow. Bonus for going
org on Google Play: **organization accounts skip the 12-tester / 14-day closed-testing
gate** that personal accounts (created after Nov 2023) must pass before production
(see §3A). That alone can save 2 to 3 weeks on a first launch.

---

## 1. STAGE 1: Dev preview (Expo Go) — free, instant, limited

Use this to eyeball UI changes in seconds. **Limitation: connecting a new source
(Gmail/Drive/etc.) will NOT complete in Expo Go**, because Expo Go cannot register
our `productivityapp://` scheme, so the OAuth popup can never return to the app.
Login and browsing the feed work fine. For the full connect flow you need a real
build (Stage 2).

### How it works
1. Install **Expo Go** from the App Store / Play Store on the phone.
2. On the Mac, from `mobile/`:
   ```bash
   npx expo start
   ```
   This prints a QR code and a URL like `exp://192.168.0.104:8081`.
3. Connect the phone (phone and Mac must be on the **same Wi-Fi**):
   - **Android:** scan the QR from inside Expo Go.
   - **iOS:** scan the QR with the Camera app (opens Expo Go).
   - **Or type the URL manually** in Expo Go > "Enter URL manually":
     `exp://<mac-lan-ip>:8081`.

### Expo Go SDK version must match the project (common gotcha)
Expo Go only runs projects whose SDK it supports. This project is **SDK 57**, so
Expo Go must be a build that supports SDK 57. If Expo Go says **"incompatible SDK
version"** (e.g. your Expo Go is 54.x supporting SDK 50–54), the Play Store may not
yet offer a newer Expo Go to your device. Options:
- Install the latest Expo Go **APK directly** from `https://expo.dev/go` (pick the
  build for the project's SDK), bypassing the Play Store. Only if a matching build
  exists there.
- **Better: skip Expo Go and build a `preview` APK (Stage 2A).** It bundles the
  correct runtime, does not depend on Expo Go, and is the only way to exercise the
  full source-connect flow anyway.
- Do NOT downgrade the project SDK just to fit an old Expo Go; that is backwards and
  risks breaking dependencies.

### If the QR does not show / cannot connect
- A backgrounded `expo start` (started by a script or tool) does **not** draw the
  QR. The QR only renders in an interactive terminal. Run `npx expo start` yourself
  in a normal terminal to see it.
- The QR content is just the `exp://<lan-ip>:8081` URL. Entering that URL manually
  in Expo Go is equivalent to scanning.
- Find the Mac LAN IP: `ipconfig getifaddr en0`.
- Different networks (phone on cellular, Mac on Wi-Fi)? Use a tunnel:
  ```bash
  npx expo start --tunnel
  ```
  (First run may prompt to add `@expo/ngrok`.)

---

## 2. STAGE 2: Friends / private beta — no public store, mostly free

Goal: let friends actually use the app (full flow, real source connections) before
you monetize. **The path is completely different on Android vs iOS.**

### 2A. Android — "just send them a file". Easiest path, free.

Yes: you build one **APK** file and anyone can install it. No store, no review, no
per-tester fee, any number of people. The APK registers our scheme, so the full
connect flow works (unlike Expo Go).

One-time setup:
```bash
npm install -g eas-cli      # or use `npx eas-cli` everywhere, no global install
npx eas-cli login           # log in to your Expo account (free)
```
Build the APK:
```bash
npx eas-cli build --profile preview --platform android
```
- `preview` is already configured in `eas.json` to output an installable `.apk`
  (`android.buildType: "apk"`) with the right env baked in.
- EAS returns a **download link + QR**. Share it. Testers open it on their phone,
  allow "Install unknown apps" once, and install.

Ways to deliver the APK:
- The EAS build link directly (simplest).
- **Firebase App Distribution** (free): nicer tester management, email invites,
  update notifications. Upload the APK there.
- Or literally send the `.apk` over WhatsApp / Google Drive.

Cost: **free** (EAS free tier covers occasional builds; heavy use may need a paid
EAS plan or local builds).

**Reach, sharing, and limits (Android APK):**
- **Shareable to anyone. No Expo org membership needed.** Org membership is only for
  people who build/manage the project; testers just need the APK link. Do NOT add
  testers to the Expo org.
- **No install cap.** Unlimited people can install and run the APK. Running the app
  uses YOUR backend, not Expo, so it consumes no EAS quota. EAS free-tier limits are
  on builds (15 Android/month) and EAS Update users (1,000), not on installs.
- **The real limits are on your side, not Expo:** one EC2 backend + Redis + the
  classifier (Gemini) + Composio. A handful of testers is fine; dozens all connecting
  Gmail and refreshing can hit Gemini/Composio rate limits or plan caps and stress
  one box. Watch those as it grows.
- **Link expiry (free tier, ~30 days):** the EAS build download link expires after
  ~30 days. IMPORTANT: this affects **new downloads only**. Anyone who already
  installed is **unaffected** — the app stays on their phone and keeps working. For a
  permanent link, download the `.apk` once and host it yourself (Google Drive /
  Firebase App Distribution), or just rebuild (each build counts against the
  15/month free quota; there is no separate "link" limit or cost).
- **Android only.** iPhone testers need TestFlight (Stage 2B, $99/yr Apple account).

**Updating installed testers:**
- Native change (new dependency, scheme, icon, etc.): rebuild the APK and reshare.
- JS-only change: `npx eas-cli update --branch preview` pushes an OTA update to
  installed apps with no reinstall (free up to 1,000 monthly users).

### 2B. iOS — you CANNOT just send a file

Apple blocks arbitrary `.ipa` sideloading for normal users. There is no free
"send a file" route. Options:

- **TestFlight (recommended).** Needs the **Apple Developer Program ($99/year)**,
  but no public App Store listing and only a light review for the first build.
  Invite friends by email or a public TestFlight link; they install via the
  TestFlight app. Up to **10,000** external testers.
  ```bash
  npx eas-cli build --profile production --platform ios
  npx eas-cli submit --platform ios          # uploads to App Store Connect
  ```
  Then in App Store Connect > TestFlight, add testers / create a public link.
- **Ad-hoc.** Register each device's UDID (max **100**), build ad-hoc, distribute
  the `.ipa` via a link. More friction than TestFlight. Still needs the $99 account.
- **Expo Go.** Free, no account, but partial demo only (no source-connect).

Bottom line: **any real iPhone testing costs $99/year.** There is no way around it.

### 2C. Alternative app stores
- **Android:** Amazon Appstore, Samsung Galaxy Store, APKPure, F-Droid (open source
  only). All viable, but for a friends beta they add friction vs a direct APK. Skip.
- **iOS:** effectively none worth using (EU alternative marketplaces are region-locked
  and heavy). Not relevant here.

---

## 3. STAGE 3: Public launch on the stores

### 3A. Google Play Store

**Fee:** **$25, one-time** (developer registration).

**Requirements (all mandatory before approval):**
- Google Play Console account ($25). Personal accounts need ID verification.
- **Closed testing gate (personal accounts only):** Play developer accounts
  registered as **personal** and created after Nov 13, 2023 must run a closed test
  with **at least 12 testers opted in for 14 CONTINUOUS days** before they can apply
  for production access (Google lowered the number from 20 to 12 around Dec 2024).
  **Organization accounts are exempt** — the rule is scoped to personal accounts; the
  trade for an org account is the D-U-N-S business verification. See "How to run the
  closed test" below. This adds ~2 to 3 weeks to a personal-account first launch.
- **Privacy Policy URL** (hosted, public).
- **Data safety form** (declare data collected: email, connected-account data, etc.).
- **Content rating** questionnaire (IARC).
- **Target API level**: must target a recent Android API (Google raises the floor
  yearly). EAS handles this via the current Expo SDK.
- **App signing**: use Play App Signing (EAS manages the upload key).
- Store listing assets: app icon, **feature graphic**, at least 2 screenshots,
  short + full description.

**Steps:**
```bash
npx eas-cli build --profile production --platform android   # produces an .aab
npx eas-cli submit --platform android                       # uploads to Play Console
```
Then in Play Console: fill the listing, run closed testing if required (see below),
then apply for production access.

**How to run the closed test (personal accounts only):**
1. Upload the app as an **AAB** (`eas build --profile production --platform android`
   produces one).
2. Play Console > **Testing > Closed testing > Create track**, attach the release.
3. Add **>= 12 testers** by email list or a Google Group. Each tester opens the
   generated **opt-in web link**, accepts, and installs **through the Play Store**.
4. Keep at least 12 opted-in for **14 consecutive days**. If testers drop below 12,
   continuity breaks and the 14-day clock resets.
5. Apply for production access from the Dashboard. Google reviews testing engagement
   + app quality; review is usually within 7 days.

Tester rules that bite:
- A **direct APK does NOT count.** Testers must join via the opt-in link and install
  via Google Play; sideloading registers nothing toward the 12/14 counter. (So the
  Stage 2A APK beta and this closed test are separate exercises unless your friends
  also opt in through Play.)
- Each tester needs a real **Android device + Google account**.
- Realistic wall-clock: **~2 to 3 weeks** (14 continuous days + up to ~7 days review),
  assuming no tester attrition.
- **Organization accounts skip this entirely** and can go straight toward production.

### 3B. Apple App Store

**Fee:** **$99/year** (Apple Developer Program). Same account covers TestFlight.

**Requirements (all mandatory before approval):**
- Apple Developer Program membership ($99/yr).
- **Privacy Policy URL** (hosted, public).
- **App Privacy** "nutrition labels" in App Store Connect (declare data collected).
- **In-app Account Deletion.** Apple **requires** an in-app way to delete the
  account for any app with account sign-up. **We do not have this yet** (we have
  signup but no delete path). This must be built before App Store submission.
- **Sign in with Apple**: required only if you offer third-party/social login
  (Google/Facebook login). We use our own email+OTP, so **not triggered** today.
  If we ever add "Sign in with Google" to the app, Apple then requires offering
  Sign in with Apple too.
- Screenshots for required device sizes; description; keywords.
- Compliance with App Store Review Guidelines.

**Steps:**
```bash
npx eas-cli build --profile production --platform ios       # produces an .ipa
npx eas-cli submit --platform ios                           # uploads to App Store Connect
```
Then in App Store Connect: fill privacy + listing, submit for review. Review is
usually 1 to 3 days.

---

## 4. Monetization (when you add the paywall)

**Hard store rule:** digital subscriptions and any paywall for in-app digital
features **must** use **Apple StoreKit** and **Google Play Billing**. You **cannot**
use Stripe for in-app digital subscriptions on iOS/Android. (Stripe is fine for a
**web** app, which takes no store cut.)

**Store commission:** 15%–30% of in-app revenue. 15% under Apple's/Google's
small-business programs and for subscriptions after year one; 30% otherwise.

**Recommended implementation: RevenueCat** (`react-native-purchases`). Industry
standard, one SDK across both stores, handles receipts, entitlements, and ships
paywall templates. Free until ~$2,500/month tracked revenue, then a small %.
Requires a real build (not Expo Go).

Flow:
1. Define products (e.g. monthly + annual subscription) in **App Store Connect**
   and **Google Play Console**.
2. Mirror them in **RevenueCat**; group access behind an **entitlement** (e.g.
   `pro`).
3. Gate premium features on that entitlement; show a **paywall** screen to
   non-subscribers.

---

## 5. The Google OAuth restricted-scope caveat (important, but not a blocker yet)

The app reads **Gmail, Google Calendar, and Google Drive**. Gmail-read and Drive are
Google **"restricted scopes."** For an app's **own** Google OAuth client, Google
requires **OAuth app verification + an annual third-party security assessment
(CASA)** before exceeding **100 users**. That assessment is expensive (thousands to
tens of thousands per year) and slow. It is the real gate to a large public launch,
bigger than any app-store step.

**Where we stand today:** OAuth runs through **Composio's** Google app (the consent
screen says "Composio wants to access your Google Account"). Composio is the verified
OAuth application; they hold the Google verification and the CASA security assessment
for these restricted scopes. Our app just asks Composio to broker the connection.
That means:
- **The verification/CASA burden sits with Composio, not us.** We do not run, submit,
  pay for, or maintain the Google security assessment. Our only cost here is our
  **Composio plan** (per their pricing / connected-account limits), not Google's
  assessors. This is the whole reason a broker like Composio is worth it early: it
  turns a slow, expensive compliance project into a line item on a SaaS bill.
- A **friends beta and even a public launch can run without us doing any Google
  verification**, as long as we stay on Composio's managed auth and within their plan
  limits.

**The trade-offs to be aware of (why you might still move off it later):**
- **Branding:** the consent screen says "Composio," not our app name. Fine for a
  beta; less ideal for a polished branded product.
- **Data path & dependency:** account access is brokered through Composio, so we
  depend on their uptime, pricing, and terms, and user data flows through them.
- **If we ever switch to our OWN Google OAuth client** (to get our name on the consent
  screen and own the relationship), the full burden becomes ours: OAuth app
  verification + annual CASA assessment + the 100-user cap while unverified. That is a
  deliberate, budgeted decision for later, not something forced on us now.

Net: **run it through Composio for now** (pay Composio, skip Google verification).
Revisit only when branding/independence justifies taking on the CASA cost yourself.

---

## 6. One-time setup checklist

- [x] `ios.bundleIdentifier` + `android.package` in `app.json`
- [x] `eas.json` with development / preview / production profiles + baked env
- [ ] Expo account + `eas-cli` logged in
- [ ] App icons / adaptive icons finalized (Android adaptive icon already wired)
- [ ] **Hosted Privacy Policy URL** (needed by BOTH stores)
- [ ] **In-app account deletion** flow (needed by Apple)
- [ ] Google Play Console account ($25) when ready for Play
- [ ] Apple Developer Program ($99/yr) when ready for iOS device testing or App Store
- [ ] RevenueCat account + products (only when adding the paywall)
- [ ] Stable backend domain (replace the `sslip.io` IP URL before real testers; the
      sslip.io host is tied to the EC2 IP and breaks if that IP changes)

---

## 7. Cost summary

| Item | Cost | When |
|---|---|---|
| Expo Go dev preview | Free | Now |
| EAS Build (occasional) | Free tier | Now |
| EAS Build (heavy) | ~$99/mo or per-build | Optional |
| Android APK friends beta | Free | Stage 2 |
| Google Play registration | $25 one-time | Stage 3 (Play) |
| Apple Developer Program | $99 / year | Stage 2 (iOS) & 3 (App Store) |
| RevenueCat | Free < ~$2.5k/mo revenue | Monetization |
| Store commission | 15–30% of IAP revenue | Monetization |
| Google restricted-scope CASA | Thousands+/yr | Only if we move to our own OAuth client |

---

## 8. Command quick-reference (run from `mobile/`)

```bash
# Dev preview
npx expo start                 # QR + exp:// URL (interactive terminal)
npx expo start --tunnel        # cross-network

# One-time
npx eas-cli login
npx eas-cli build:configure

# Android friends-beta APK (send the resulting link)
npx eas-cli build --profile preview --platform android

# iOS TestFlight (needs $99 Apple account)
npx eas-cli build --profile production --platform ios
npx eas-cli submit --platform ios

# Play Store production
npx eas-cli build --profile production --platform android
npx eas-cli submit --platform android

# OTA JS-only update to an existing build (no rebuild)
npx eas-cli update --branch production
```

---

## 9. Recommended sequence for right now

1. **Android friends:** build the `preview` APK and share the link. Free, immediate,
   full flow works.
2. **iPhone friends (only if needed):** pay the $99, use TestFlight.
3. Before a public launch: host a Privacy Policy, add in-app account deletion, move
   the backend to a stable domain, then decide on Play ($25) / App Store ($99/yr),
   add RevenueCat for the paywall, and budget for Google's own-OAuth verification.

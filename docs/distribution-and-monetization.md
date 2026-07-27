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
- **Closed testing gate (new accounts):** personal developer accounts created after
  Nov 2023 must run a **closed test with at least 20 testers opted in for 14
  continuous days** before they can apply for production access. Your friends beta
  (Stage 2A, via a Play closed-testing track) can satisfy this. Plan for it: it adds
  ~2+ weeks to first launch.
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
Then in Play Console: fill the listing, run closed testing (20 testers / 14 days if
required), then promote to production. Review is usually hours to a few days.

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
screen says "Composio wants to access your Google Account"). That means the
verification/CASA burden sits with **Composio, not us**. So:
- A **friends beta works with no Google verification on our side.**
- The wall only appears if/when we migrate to our **own branded** Google OAuth
  client (so the consent shows our app name instead of "Composio"). At that point
  the verification + CASA + 100-user-unverified-cap become ours. Plan and budget for
  this before a branded public launch.

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

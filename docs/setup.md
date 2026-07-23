# Setup steps

What is done, and the exact steps for what is left.

## Done

| Item | Status |
|---|---|
| Composio API key | In `.env` as `COMPOSIO_API_KEY`, validated |
| Supabase URL + anon + service role | In `.env`, validated format |
| OpenRouter key + model | In `.env`, **live-tested**, `google/gemini-2.5-flash` responding |

`.env` is gitignored. Nothing secret is committed.

> **Rotate the Supabase service role key.** It was pasted into a chat transcript. Supabase dashboard, Settings, API, "Reset service role key", then update `.env`. It bypasses row-level security, so it is the one key worth treating as compromised.

---

## 1. Connect GitHub under the API key's project

**The problem:** your CLI already has GitHub connected, but under a different project than the API key points at. The SDK therefore sees **0 connected accounts**. Both paths below fix it. The dashboard one is easier.

### Path A: dashboard (recommended)

1. Go to **https://platform.composio.dev** and sign in.
2. Top-left, open the **project switcher** and select **`vicky_workspace_first_project`**. This is the project your API key belongs to (`pr_XrurfuScSbKj`).
3. Open **Auth Configs** in the sidebar. If there is no GitHub auth config, click **Create**, choose **GitHub**, and pick **Composio-managed auth** (no OAuth app of your own needed).
4. Go to **Connected Accounts**, click **Add / Connect account**, choose **GitHub**.
5. It opens GitHub's authorize screen. Approve.
6. Confirm the row appears with status **ACTIVE**.

Then tell me, and I will verify from this side with one read-only call.

### Path B: CLI

Run these from the repo root:

```bash
cd /Users/vickypandey/Desktop/agentiwise/productivity-app && ~/.composio/composio dev init
```

Pick **`vicky_workspace_first_project`** when it asks. This binds this folder to the same project as the API key. Then:

```bash
cd /Users/vickypandey/Desktop/agentiwise/productivity-app && ~/.composio/composio dev connected-accounts link github
```

Follow the browser flow, then verify:

```bash
cd /Users/vickypandey/Desktop/agentiwise/productivity-app && ~/.composio/composio dev connected-accounts list
```

You should see a GitHub row with status `ACTIVE`.

### Later, the same way

Repeat for `slack`, `googlecalendar`, `googledrive`, `linear`, `gmail` as each phase arrives. Managed auth means **no OAuth app to register for any of them**.

---

## 2. Expo: what it is and why we need it

**What it is:** Expo is a toolkit and a hosted service that sits on top of React Native. React Native is the framework; Expo is what makes it practical to build, run and ship.

**Why we need it, concretely:**

1. **Run on a real phone in seconds.** With the Expo Go app, you scan a QR code and the app appears on your phone. No Xcode, no Android Studio, no build step. This is how you will test daily.
2. **Push notifications.** This is the big one. Sending a notification normally means dealing with Apple's APNs certificates and Google's FCM separately. Expo's push service wraps both behind one API, so our backend sends to one endpoint and Expo routes to the right platform. Without it we would be managing Apple certificates by hand.
3. **Building the installable file.** EAS Build compiles the `.apk` (Android) and `.ipa` (iOS) **in the cloud**. You get an APK you can send anyone, without a local Android toolchain.
4. **Over-the-air updates.** Ship JS changes to installed apps without going through app store review.

**Do you need an account?**
- To test on your own phone with Expo Go: **no account needed.**
- To build an APK, or to send push notifications: **yes, free account.**

**Steps (about 3 minutes):**

1. Create a free account at **https://expo.dev/signup**.
2. Install the CLI:

```bash
npm install -g eas-cli
```

3. Log in:

```bash
eas login
```

4. Install **Expo Go** on your phone from the App Store or Play Store.

That is all until we have an app to build. Cost: free tier covers development, and push notifications are free.

---

## 3. Deployment (when we get there)

The backend needs one stable public HTTPS URL for Composio webhooks. Recommended: a small always-on container (Railway, Render or Fly, roughly $5/month), or a t4g.small EC2 if you prefer control. Not Vercel, because serverless timeouts will cut off batched LLM summarization. Reasoning in [architecture.md](architecture.md) section 5.

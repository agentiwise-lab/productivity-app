# Mobile sentiment: Mobbin, Reddit, YouTube, Dribbble

**Date:** 2026-07-24
**Part of:** step 1 research, mobile-only pass. Replaces [06-social-sentiment.md](06-social-sentiment.md) §9 and §10.
**Method:** logged-in Chrome, read-only. Nothing posted, liked, submitted or logged into.

---

## 1. Mobbin: the mobile reference library, and its taxonomy

**Login state: not logged in.** The full library, flows and screen search sit behind a wall. **No account was created and no login attempted.** What follows comes from `mobbin.com/explore/mobile` and `mobbin.com/awards`, both public.

**Scale:** 1,428 apps, 621,500+ screens, 323,900 flows. Mobile is first in the nav.

### The three-axis taxonomy, which is the most valuable thing on the site

Every screen is tagged on all three axes at once. **This is worth copying as our own vocabulary:**

1. **Screens** (the page type): Home, Wallet and Balance, Calendar, Browse and Discover, Dashboard, Profile, Settings, Login, Account Setup, Subscription and Paywall, Splash, Welcome, Checkout.
2. **UI Elements** (the component), in five buckets: **Control** (Button 50,956 screens, Accordion 2,171, Checkbox 2,456), **Imagery** (Avatar 11,073, Illustration 10,110), **Overlay** (**Bottom Sheet 19,017**, Coach Marks 2,195, **Action Sheet 202**), **View** (Card 15,386, Banner 4,361, Badge 4,122).
3. **Flows** (the verb): Logging In, Onboarding, Subscribing, Filtering and Sorting, Searching, Adding and Creating, **Logging and Tracking**, Switching View, Saving to Collection, Deleting.

**Two numbers carry real signal:**

- **Bottom Sheet 19,017 vs. Action Sheet 202.** Modern iOS has **almost entirely abandoned the native action sheet in favour of the custom bottom sheet.** A ~94:1 ratio is not a preference, it is a convention change.
- **Coach Marks at only 2,195.** Onboarding overlays are far rarer than designers assume.

**Flows are shipped three ways: video (with micro-interactions intact), interactive prototype, and static screens.** That video-of-the-flow is a first-class artefact is itself the finding: **on mobile, motion is treated as part of the spec, not as decoration.**

### Trending apps and what they actually look like

Currently trending: Open, KakaoBank, Nextdoor, **stoic.**, Plata Card, Trust Wallet, Ultrahuman, **On**, Chipotle, Walmart, **Vipps**, **Saturn Calendar**.

- **stoic.** Near-monochrome. Warm off-white ground, one near-black rounded card (~20px radius) carrying the day's prompt in **centred light-weight type with a tiny uppercase letterspaced eyebrow** ("Morning Preparation", "Day 6 of 7"). Actions are **outlined pill buttons, not filled**. 5-slot tab bar with a **solid black circular FAB in the centre slot**, flanked by hairline outline icons with 9 to 10px labels. **Almost zero colour; all hierarchy carried by weight and space.**
- **Vipps.** A **floating orange pill action bar docked above the tab bar**, four icon-over-label columns. List rows are inset rounded-rect groups with a circular monogram avatar, two-line title and subtitle, right-aligned amount plus chevron. Section labels small, sentence case, generously spaced.
- **Saturn Calendar.** Content sits in a **bottom sheet with a visible grab-handle pill**. Agenda rows are full-width tinted chips with a leading glyph. Date headers repeat ("Today, Jul 10") with a pill status chip at the right. A persistent inline composer pinned above a **3-slot** tab bar.
- **On.** Editorial commerce. **Filter chips are plain text with an underline for active state: no pills, no borders.** Micro-caps letterspaced eyebrow, monospace-flavoured product name and price. A floating black "Menu" pill **deliberately overlaps the tab bar**, breaking its plane.

> **stoic. and Vipps are the two most directly relevant to us.** stoic. proves a near-monochrome, weight-driven hierarchy reads premium. Vipps' list rows are almost exactly the shape our feed rows want to be.

### Mobbin Awards, community-voted with a named curator panel

Curators include Andy Allen (Not Boring Software), Rafael Conde (Retro), Tobias van Schneider (mymind), Sara Vienna (Metalab), Joey Banks.

| Category | Winner | Share | Other nominees |
|---|---|---|---|
| **iOS App of the Year** | **Headspace** | 28% | Open, Suno, Arc Search, **Family**, Tolan |
| Innovator of the Year | Claude | 43% | Doji, ElevenLabs, Cursor, PamPam |
| Animator of the Year | **Duolingo** | 29% | Airbnb, Luma AI, mymind, Cosmos |

Citations, verbatim: Headspace is **"a masterclass in designing for calm without losing clarity"**, with a "punchy palette that cuts through the typical wellness space". Duolingo: **"Every interaction is purposeful, making feedback and progress immediately felt."**

> **Note the nuance on Duolingo.** It wins *Animator* of the Year for purposeful motion, while [05](05-gamification-that-stays-premium.md) documents its streak mechanics as the manipulative counter-example. **Both are true.** Steal the motion craft, not the streak psychology.

---

## 2. Reddit, mobile subreddits only

### The single most concrete mobile critique found

**[r/iosapps, "It took us 9 months to get our app here"](https://old.reddit.com/r/iosapps/comments/1n2cq3d/it_took_us_9_month_to_get_our_app_here/)** — **498 points, 198 comments.**

The praise is visceral and tactile: **"The UI is actually insane."** / **"I'm finding myself opening the app just to swipe around."**

Then a working UI designer lists exactly what still reads as amateur, and **four of the five apply to us**:
- **"Current day marker is too similar to a notification badge"** — a filled dot reads as unread state, not selection. Use an outline instead. *(We use filled tier pips.)*
- **"menu icon is too ambiguous and most modern apps are designed with navigation on the bottom rather than the top."**
- **"all of the icons in the top nav seem a bit small"**, questioning whether they meet HIG tap-target minimums.
- **"loading screen design seems unfinished."**
- The score renders 100 for every day with no data connected: **"I'd assume some sort of placeholder would work better."** An empty state faked as a full state.

### On app icons, where the sub rejected the premise outright

**[r/iOSProgramming, "I think app icons matter way less than designers think"](https://old.reddit.com/r/iOSProgramming/comments/1suy1vv/i_think_app_icons_matter_way_less_than_designers/)** — net 0 points, 25 comments, and the sub overwhelmingly disagreed:
- "Tons of apps have icons that immediately identity them as trash."
- "icons dont sell apps but ugly ones get buried in folders fast."
- **"An icon needs to be good enough to indicate to the user that the app is well made."**
- **"How you do one thing is how you do all things."**

One developer claims icon changes produce "double digit lift" in App Store conversion even for established apps.

### What designers actually named

**[r/UXDesign, "What are some best-designed apps currently?"](https://old.reddit.com/r/UXDesign/comments/1losym7/what_are_some_bestdesigned_apps_currently/)** — 69 points, 76 comments, explicitly scoped to mobile.

Named: **Not Boring** (blanket "any app by"), Grit, PoolSuite FM, Airbnb, **How We Feel**, Wise, **Flighty**, Hinge, Notion (contested), Apple Music (contested).

**The most important finding in this thread is a negative one.** Notion gets praised as a product then immediately undercut **on mobile specifically**: "Notion's Android Mobile app is so glitchy and not great", and on iOS, "Neither the IOS, from a designer's pov." **Web reputation does not transfer to phone.** That is the exact error you caught me making.

Other useful notes: How We Feel praised for "taking it from a simple input to a discovery journey." Hinge praised for restraint: **"It doesn't do any more than it needs, but it does what it has to well."** Spotify criticised for having "gotten too crowded". Apple Music attacked for "random elements in different menus".

### Where design effort actually pays on mobile

**[r/iOSProgramming, "App Store Design Cheatsheet (2026)"](https://old.reddit.com/r/iOSProgramming/comments/1tas0zv/app_store_design_cheatsheet_2026/)** — 163 points. Store-listing rather than in-app, but the numbers reframe the priority:
- Visual opinions form in **~50ms** and do not shift with longer viewing.
- **~60% of App Store visitors never scroll past the first screenshot.**
- **Under 2% tap "Read more".**

Commenters were surprised: "It's shocking that only 2% read below the fold."

### Category convention beats novelty

**[r/iOSProgramming, analog camera app critique](https://old.reddit.com/r/iOSProgramming/comments/1npgnyt/i_am_designing_a_simple_analogstyle_camera_app_in/)** — 169 points, 92 comments: "it makes sense to follow the lead of the stock app and apps like **Halide** which are dark. Photo editors also make this choice." Detail nitpicks dominated, including **two centre buttons not being optically aligned.**

### Honest coverage note

r/iosapps and r/androidapps are dominated by self-promotion. **No substantive design thread was found in r/androidapps at all.** Of the watchlist, only **Flighty, How We Feel, Not Boring, Arc Search and Halide** surfaced. **No Reddit discussion whatsoever** was found for Things 3, Bear, Craft, Structured, Copilot Money, Oura, Whoop, Gentler Streak, Streaks, Amie, Fantastical, Overcast, Reeder or Mela. Their place in the shortlist rests on Apple's own citations and design press, not on community sentiment.

---

## 3. YouTube

| Title | Channel | Views | Mobile-specific techniques named |
|---|---|---|---|
| Everything about Mobile App UI's in 8 minutes | Kole Jain | 81k | Chapters: **Navigation, Scale, Content, One Screen One Job, Gestures, Dynamism, Empty States** |
| **How I Make Apps FEEL 10x Better (5 Design Secrets)** | Chris Raroque | **202k** | **Interactions and Animations, Custom Illustrations, Haptic Feedback, Good Icons, Design Taste.** Description: "studying the top iOS apps out there" |
| My App Design Process | Chris Raroque | 74k | Moodboard, Figma prototype, then **testing on a real device**; concrete revisions to filtering, icon side, indicator cleanup |
| **WWDC25: Design foundations from idea to interface** | Apple Developer | 131k | Structure, Navigation, Content, Visual Design. First-party canon |
| The Secret Behind Weirdly Addictive Apps | Tim Gabe | 427k | Highest-view in the set |
| Play: The Secret Weapon for iOS Devs | Sean Allen | 59k | Previewing animations **on a physical device**, exporting SwiftUI to Xcode |

**The two most-viewed genuine mobile-UI tutorials are both Mobbin-sponsored**, which independently corroborates that Mobbin owns this niche. Disclosed as commercial, not evidence.

Discarded as web: "The Psychology of Premium Websites" (273k), despite ranking high on "app design that feels expensive".

---

## 4. Dribbble, mobile

**The most useful methodological finding:** the `mobile app tab bar` query is **by far the highest-signal of the four run**, because it forces the component into frame at actual size and strips away the mockup theatre. The `ios app` and `ios productivity app` grids are dominated by agency concept work on 3D-rendered phone bodies floating over gradient backdrops. **Engagement there rewards the render, not the interface.**

| URL | Designer | Likes / Views | What it shows |
|---|---|---|---|
| [freud v3 tab nav bar](https://dribbble.com/shots/27185623-freud-v3-AI-Mental-Health-App-Mobile-Tab-Nav-Bar-UI-Component) | strangehelix | 227 / 41.4k | **The strongest tab-bar study on the site.** Floating fully-rounded pill **detached from the screen edge** with ~16px side margin, light and dark pair. 5 icon-only slots, ~20px hairline outline glyphs, active slot is a **filled circular chip** rather than a colour swap. Soft ambient shadow, no border |
| [asklepios smart tab bar](https://dribbble.com/shots/26882253-asklepios-v3-AI-Health-Wellness-App-Smart-Mobile-Tab-Bar-UI) | strangehelix | 215 / 38.9k | Same floating pill, but the active tab **expands a popover above itself** listing sub-destinations with count badges. **Solves 5-tab overflow without a hamburger** |
| [freud v3 icon-over-label](https://dribbble.com/shots/27122946-freud-v3-AI-Mental-Health-App-Mobile-Tab-Navigation-Bar-UI) | strangehelix | 201 / 35.2k | Dark charcoal pill over photographic ground, **icon-over-label with ~9px labels** kept deliberately tiny so the bar stays ~64px |
| [Hybrid Tab Bar + Segmented Control](https://dribbble.com/shots/27143363-Hybrid-Tab-Bar-Segmented-Control) | Ionut Zamfir | 205 / 38.6k | **Segmented control stacked directly on top of the tab bar in one container.** Keeps primary nav and local filter in one thumb zone |
| [Animated Tab Bar Icons](https://dribbble.com/shots/1766396-Animated-Tab-Bar-Icons) | Ramotion | **2.2k / 298k** | Highest engagement in the tab-bar set. The icon-morph timing is the content |
| [Meditation iOS App](https://dribbble.com/shots/27201897-Meditation-iOS-App) | Fireart Studio | 100 / 23.9k | Genuinely restrained. Near-black, **full-bleed photography with type laid directly over it, no cards.** Transport controls are hairline circular outlines |
| [Task Manager iOS](https://dribbble.com/shots/23079473-Task-Manager-Mobile-IOS-App) | QClay | 1.6k / 687k | **Big numeric display type ("78%")**, one yellow accent against greyscale. The metric occupies roughly a third of the card |
| [Personal Finance iOS](https://dribbble.com/shots/24622160-Personal-Finance-iOS-App) | Fireart Studio | 1.2k / 694k | Highest-view iOS shot found. Light, airy, generous vertical rhythm |
| [Fintech Dark Mode](https://dribbble.com/shots/26010654-Fintech-Mobile-App-Dark-Mode-UI) | Budiarti R. | 78 / 31.9k | Best of the dark search: near-black, single yellow accent, hairline dividers |
| [TaskEz UI Kit](https://dribbble.com/shots/14630301-TaskEz-Productivity-App-iOS-UI-Kit) | UI8 | 2.8k / 712k | Highest-engagement productivity shot, **but it is a commercial UI kit**, so it reads as the *default* premium look rather than a differentiated one |

---

## 5. 21st.dev: the verdict you asked for

**It has essentially nothing for mobile app design, and this can be said with numbers rather than impressions.**

Its taxonomy is entirely web-shaped: Heroes 1,152, Forms 1,522, Cards 1,780, Buttons 2,043, Navigation Menus 477, Sidebars 95, Footers 65, Pricing Sections 216, plus Marquees and Shaders. **There is no Tab Bar category, no Bottom Sheet category, no App Bar, no Segmented Control, no Pull-to-Refresh, and nothing gesture- or haptics-related.**

Searching "mobile" returns a header reading **"Browse 5 Mobile components"**, and the hits split three ways:
1. **iPhone chrome for showing off web work** (Iphone Mockup 63 installs, IPhone 15 Pro 64, Phone Mockups 52).
2. **Responsive-breakpoint hooks** (Use Mobile 33, UseScreenSize 71).
3. A thin tail of React re-implementations of phone patterns (BeUI Bottom Sheet 18, Swipe Row 13, Wheel Picker 40, Drawer 21).

Every one of those is **two to three orders of magnitude below the site's real hits**, which are scroll-animation heroes and gradient shaders for landing pages.

**It is a React/Tailwind/Next.js registry for marketing sites.** Its "mobile" tag mostly means "renders acceptably at 375px" or "is a picture of an iPhone."

**Recommendation: drop it from this research track entirely.** The blocking onboarding form was present; it was not filled or submitted, and the page was read through the DOM instead.

**Mobbin is the correct substitute**, and it is the only source with a real three-axis mobile pattern taxonomy.

---

## 6. Synthesis: what makes a mobile app read premium

Ranked by how consistently the signal appeared across all four sources. **[M]** marks signals that are mobile-specific and would not transfer to web.

1. **Navigation lives at the bottom, and the bar itself is the brand statement. [M]** The most repeated signal by a distance. The Reddit critique that landed hardest on an otherwise-loved app was "most modern apps are designed with navigation on the bottom rather than the top." Mobbin tags Tab Bar on nearly every trending screen. The strongest Dribbble work is *entirely* tab-bar studies. **The 2026 premium move is a floating rounded pill detached from the screen edge, with the active state as a filled circular chip rather than a colour change.** On web a nav bar is furniture. On mobile it is the one component the thumb touches every session.
2. **Motion is spec, not polish. [M]** Mobbin ships flows as video and prototype as first-class artefacts. Duolingo won Animator of the Year. The 202k-view video leads with interactions. **Cheap apps have state changes; premium apps have transitions between states**, and on mobile the transition also teaches spatial hierarchy.
3. **Haptics. [M]** Named explicitly in the most-watched mobile design video in the set. No web equivalent. **Invisible in a screenshot, immediately felt in the hand**, which is exactly why it separates apps that look premium from apps that are.
4. **Empty states are designed, not defaulted.** The sharpest hit in the Reddit teardown was an app showing a score of 100 for every day with no data connected: **faking a full state instead of designing the empty one.** On a phone the empty state is often the whole screen with nowhere to hide.
5. **Bottom sheets have replaced modals and action sheets. [M]** 19,017 Mobbin screens against 202. **Using a centred alert dialog where a sheet belongs is now a dated tell.** The grab-handle pill is load-bearing: it signals draggability before the user tries.
6. **One screen, one job.** Hinge praised for doing "no more than it needs". Spotify criticised as "too crowded". Apple Music attacked for "random elements in different menus". **Density that reads as powerful on web reads as cluttered on mobile**, because there is a fraction of the real estate and none of the hover affordances.
7. **Category convention beats novelty.** Camera apps are dark because Halide and the stock camera are dark. **Deviating reads as inexperience, not originality. Execute the convention better; do not replace it.**
8. **The icon is a proxy for engineering quality. [M]** "How you do one thing is how you do all things." The home screen puts your icon in a grid next to Apple's own, at 60px, with no copy to rescue it.
9. **Tap targets and optical alignment at real size. [M]** Top-nav icons flagged as too small for HIG minimums; two centre buttons flagged for being a few pixels off-centre. **"Test on a real device" is a named step** in the process videos.
10. **Typography carries hierarchy where colour and chrome cannot.** The most premium examples (stoic., On, Fireart's meditation) are **near-monochrome and lean entirely on weight, size, letterspacing and a micro-caps eyebrow.** Cheap mobile design substitutes a second accent colour or a gradient for a real type scale.
11. **First impression is measured in milliseconds and screenshots. [M]** ~50ms to form a visual opinion; ~60% never scroll past screenshot one; under 2% expand the description. **On mobile the store listing is the first UI.**
12. **Predatory paywalls destroy premium perception faster than visuals build it. [M]** Hidden unsubscribe, auto-selected add-ons. This lands on a full-screen takeover the user cannot dismiss with a browser back button.

---

## Reference stack worth adopting, in order

1. **Mobbin** — dominant, and the only source with a real three-axis mobile taxonomy. A paid account would be a genuinely good spend for step 2.
2. **refero.design** and **60fps.design** — both surfaced by designers unprompted, both mobile-motion-focused.
3. **ScreensDesign** — surfaced independently in r/iOSProgramming.
4. **Dribbble**, but only for component-level queries like `mobile app tab bar`. Not for full-screen concept shots.
5. **21st.dev** — not in this conversation at all.

---

## Process notes

- No page contained text addressed to an AI agent.
- **Not logged into Mobbin, and no account was created.** The 21st.dev onboarding form was not filled or submitted.
- Mobbin sponsors the two most-viewed mobile design videos found. Disclosed as commercial.

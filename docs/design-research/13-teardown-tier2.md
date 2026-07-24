# Teardown: Not Boring Habits, Structured, Family, WHOOP, Copilot Money, stoic.

**Date:** 2026-07-24
**Part of:** step 2 teardowns. Tier 2 of the [mobile shortlist](07b-shortlist-mobile.md).

**Evidence tags:** `[published]` from the app's own words or Apple's · `[observed]` seen in a screenshot or video · `[inferred]` reasoning.

> ### Read the method limitation first
>
> This agent had WebSearch and WebFetch only, which return text-converted pages. **It could not view a single screenshot or video**, so there are **no `[observed]` tags in its own findings**. Everything is `[published]` or `[inferred]`. Where it could not source a claim it wrote `NOT FOUND` rather than dressing it up, which is the right call and is why this file has more admitted gaps than the others.
>
> Two of those gaps are closed below by the earlier Chrome pass, which *did* view screens. Those are marked and attributed.

---

## 1. (Not Boring) Habits: the craft-budget question

**ADA 2022 Delight and Fun WINNER**, and separately a **Visuals and Graphics FINALIST** the same year. Both, confirmed on [Apple's 2022 page](https://developer.apple.com/design/awards/2022/) `[published]`.

**The answer: the budget went to exactly one interaction, and Andy Allen says so outright.**

- **The rest is stock, by stated intent:** "Most of [our] standard controls are fairly off-the-shelf, which makes things very simple and predictable. **We didn't have to rethink how a button or a popover works.**" `[published]` ([Apple](https://developer.apple.com/news/?id=9ab1g4r3))
- **The hero mechanic is a press-and-hold deliberately longer than you expect**, with escalating feedback whose job is to tell you to keep holding: "It's a very big, gross interaction... But after prototyping, we found we had to make it much more intentional; **we needed feedback that told you you needed to keep holding.**" `[published]`
- Three layered channels on that one control: custom **sound**, custom **haptics**, and **3D particle animation**, tuned together. "**There were thousands of iterations**... I'd do something and think, 'OK, this is way over the top and I'm gonna do it anyway.'" `[published]`
- **Pipeline:** models in **Blender**, rendered with **SceneKit**, embedded among UIKit and SwiftUI views. SceneKit was chosen for **compositing, not rendering power**: "SceneKit's interfaces with UIKit and standard UI controls make it all feel more seamless, like one environment." `[published]`
- **The design frame is game-feel, not app-feel:** "Game designers are amazing at taking very simple inputs, like a one-button press, and turning [it] into something much bigger... The same button can feel like you're tiptoeing around or smashing something with a sledgehammer." `[published]`
- **Shipped in two months**, and the stated point was to prove richness does not require a bespoke engine: "We wanted to show how you could build custom, rich experiences with **off-the-shelf pieces**." `[published]`

**What the "shared system" across Weather, Calculator, Timer and Habits actually consists of: NOT FOUND.** Apple names the suite; nobody documents a shared grid, type scale or token set.

**Also NOT FOUND:** tab bar treatment, typography, weight strategy, empty states. The only palette characterisation is philosophical: "minimalism is a fun place to visit for me, but it's not somewhere I want to live" `[published]`.

**The transferable rule: one interaction gets thousands of iterations, everything else gets the platform default. That is a budget allocation, not a style.**

---

## 2. Structured: the timeline question

**ADA 2026 Inclusivity FINALIST, not a winner.** `[published]` ([Apple](https://developer.apple.com/design/awards/))

**The answer: the timeline is scannable because a task is a block whose height is its duration, so time becomes a spatial quantity. And the gaps are labelled, not merely empty.**

- Company's own framing: split your day into tasks and "visualize them in a timeline", combining them "into a single visual timeline" `[published]` ([structured.app](https://structured.app/)).
- **Tasks are sized by duration.** Duration comes from presets or a custom value and the block scales, so a 30-minute item reads visibly shorter than an hour `[published, third-party]`.
- **"Now" marker:** "Current time is always visible so you know what's now and what's next" `[published]`. **Its visual treatment (line, colour, pill) is NOT FOUND.**
- **The sharpest idea in the app: gaps are quantified, not blank.** "If you have breaks in your timeline, the app will let you know the amount of time left in there", and tapping the gap creates a task in it `[published]`. **The empty state of a row is itself information.**
- **Per-task identity:** colour, icon, recurrence, and an "energy level", plus subtasks and notes `[published]`.
- **Multi-day view compresses each day's timeline down to its task icons** side by side. Icon-as-identity carrying at very small scale `[published]`.
- **Gestures:** press-and-hold a task until it "pops out of the timeline", then drag, with a preview showing the drop target. Inbox items drag into the timeline to schedule `[published]` ([help.structured.app](https://help.structured.app/en/articles/3232066)). **Note this is the same lift-then-drag pattern as Things 3.**
- Per-task sheet offers edit, delete, duplicate, complete, and **"Focus Now"** which takes the single task fullscreen `[published]`.
- **Navigation is tab-based:** Inbox, Timeline, AI, Settings `[published]`. Exact styling NOT FOUND.

**Why the neurodivergent audience responds**, per the company: reducing cognitive load through tasks as **visual blocks rather than abstract bullet points**, a linear visualisation to counter **time blindness**, colour coding for fast identification, and **icons that let you navigate without reading** `[published, first-party]` ([Structured blog](https://structured.app/blog/neurodivergent-month)).

> **Correction to my own earlier wording.** I previously wrote that the neurodivergent community "praises its simple layout." **No direct user quote saying that was found.** Third-party review language is "clean and simple interface." The *mechanisms* above are first-party sourced; the *quotation* was not. Corrected.

**NOT FOUND:** row anatomy at pixel level, type scale, colour tokens, empty-day state.

---

## 3. Family: the motion question

**No Apple award** (correct). **Mobbin nomination could not be independently verified** by this agent, though the earlier Chrome pass read it directly off Mobbin's awards page.

[benji.org/family-values](https://benji.org/family-values) is unusually explicit, organised as three principles: *Simplicity through Gradual Revelation*, *Fluidity through Seamless Transitions*, *Delight through Selective Emphasis*.

**The answer: trays are the entire navigation model, and height is a semantic channel rather than a layout accident.**

- **Height carries meaning:** "To prevent any confusion during transitions, **each subsequent tray is designed to vary in height.**" Content is sometimes **rewritten** so the next tray reads at a different height `[published]`.
- **Overlay, never displace:** "Unlike full screen transitions that can displace users from where they just were, **trays overlay content directly onto the current interface.**" `[published]`
- **One tray, one job:** each holds "a singular piece of content... or a primary action" `[published]`.
- **Origin matters:** trays "can manifest either as standalone entities on top of any app content, **or emerge from within other components like buttons**" `[published]`.
- **Text morphing on shared letters:** Continue → Confirm animates around the shared "Con", so the user registers that the action escalated `[published]`.
- **Direction-matched transitions:** tapping a tab to the left moves the transition left, "a flash of directional motion" so users **"fly instead of teleport"** `[published]`.
- **Context-adaptive theming:** "within a dark-themed flow, trays adopt a darker colour scheme" `[published]`.
- **The delight budget:** **"The potential for delight increases as the frequency of feature usage decreases."** `[published]`

> **This is the single most portable idea across all seventeen apps, and it decides our animation plan.** A triage feed is by definition the highest-frequency surface in the product. **Therefore the feed row itself gets restraint, and the budget goes to the rare moments:** inbox-zero, first run, and the escalation or snooze confirmation.

### React Native feasibility, assessed `[inferred]`

| Technique | Verdict |
|---|---|
| Overlay tray with varying height | **Easy.** Layout animation plus a shared spring. The hard part is content-authoring discipline, not code |
| Direction-matched tab transitions | **Easy.** Read the tab index delta, drive `translateX` sign from it |
| Context-adaptive theming | **Easy.** Theme context, no animation cost |
| Delight-budget rule | **Free.** It is a policy, not code |
| **Shared-letter text morphing** | **Hard.** No RN primitive. Needs per-glyph measurement and independently animated character views, or Skia. **Descope or fake it** with a crossfade plus slight x-offset unless it is a signature moment |
| Numeral comma-shifting | **Medium.** Per-digit animated views, doable with a rolling-digit component |
| Matching iOS spring feel | **Medium.** Reanimated springs are capable; matching Apple's defaults is tuning, not new tech |

---

## 4. WHOOP: hero numeral and data density

**A sourcing correction that matters.** The two facts I previously treated as equivalent trace to very different quality sources:

- **Verified, first-party:** the three-colour bands are official. **GREEN 67 to 100%** (well recovered), **YELLOW 34 to 66%**, **RED 0 to 33%** (rest needed) `[published]` ([WHOOP](https://www.whoop.com/us/en/thelocker/how-does-whoop-recovery-work-101/)).
- **NOT verified: the "~72pt equivalent" hero numeral.** It comes solely from a **design-agency blog post**, and that post's author **estimates rather than measures** it `[published, secondary, unmeasured]`. **Treat as a plausible ballpark, not a spec.** I previously presented this as the one hard hero-numeral number available; that was too strong.

**Three-dial home screen, confirmed as a real product change:** three dials for Sleep, Recovery and Strain, each opening a deep-dive showing what feeds the score `[published, surfaced via search index; the support page returned 403 to direct fetch]`.

**Progressive disclosure structure** `[published, secondary]`:
- **Tier 1 Overview:** three numbers only. Recovery %, Strain on a **0 to 21** scale, Sleep as hours plus performance %
- **Tier 2 Trends:** 7-day line charts, daily bars, duration against baseline
- **Tier 3 Deep-dive:** raw biometrics. HRV trend, resting HR over 30 days, respiratory rate, skin temperature
- **Each tier is entered by a deliberate tap or swipe. Nothing auto-expands.**

**Typeface: NOT FOUND.** The only public analysis is of the **logo wordmark**, which says nothing about the in-app UI face. **Do not repeat any in-app typeface claim.** **Hex values: NOT FOUND.** Tab bar, row unit, gestures, motion, haptics, empty states: **NOT FOUND**.

**The transferable mechanic** `[inferred]`: the bands are **numeric thresholds published to users**. Users learn one mapping and it holds on every screen, so **colour does the triage before the number is read.** That is why the density does not overwhelm.

---

## 5. Copilot Money: the native-customisation question

**ADA 2024 Innovation FINALIST, not a winner.** Winners were Procreate Dreams and Lost in Play; fellow finalists were SmartGym, Wavelength and Call of Duty: Warzone Mobile `[published]` ([Apple](https://developer.apple.com/design/awards/2024/)).

**The answer: "heavily tweaked" means restyling a stock UIKit component rather than reimplementing its behaviour. And where the interaction surface got genuinely complex, they went the *other* way and adopted the stock component wholesale.**

- Apple's words: the team "managed to take core UIKit components and **mold them to what they want them to look like**, which is why the app has such a unique look and feel" `[published]`.
- Why native at all: "I believe that having a native Swift app makes a difference the moment you start interacting with it" `[published]`.
- **The interesting reversal, Swift Charts.** Self-described as extremely custom, they used stock anyway: "We tend to do things very custom... So a section like Cash Flow, which has a lot of interactive charts, would have been a lot to build from scratch like we normally would. So we thought, 'OK, maybe now is the time to take a look at Swift Charts.'" And more bluntly: **"Why should we build something from scratch if we can use what's already there?"** `[published]` ([Apple](https://developer.apple.com/articles/copilot-money))
- **The deciding factor was interaction-event surface area, not rendering:** "Now that we're on iOS, iPadOS, and macOS, we need to support a lot of user-interaction events. **Swift Charts saved us from having to manage a lot of custom event types in custom components.**" `[published]`
- Unexpected payoff: "Because these features involve less code and fewer UI components, **finding and fixing bugs is super-easy.**" `[published]`
- Cash Flow was **their first shipped SwiftUI feature** `[published]`.
- **On-device ML** categorises transactions "on your device, not in the cloud" `[published]`.

**Three corrections to what I previously wrote:**
- **"Kept data local for responsiveness" is NOT what the sources say.** They say ML categorisation is on-device for **privacy**. No source attributes local storage to responsiveness. **Do not repeat my earlier phrasing.**
- **The animated budget dials: NOT FOUND.** No source describes them.
- **The Face ID moment: NOT FOUND.** No source describes it.

Typography, palette, tab bar, row unit, gestures, haptics, empty states: **NOT FOUND**.

---

## 6. stoic.: the near-monochrome question

**This is the weakest-sourced entry, and the agent was blunt about it: it could not verify a single specific visual observation**, because it could not view images.

**What it could source:**
- The interface is "stark... almost entirely black and white, and deceptively simple" `[published, secondary]` ([MobileSyrup](https://mobilesyrup.com/2019/06/09/stoic-self-reflection-journaling-app-review/)).
- **What actually carries emphasis, per the sources: continuous micro-feedback and live state, not colour.** Concretely, the sleep-quality slider **updates its descriptive text in real time as you drag** — the label is the feedback channel. Also: streak counters appearing after first completion, badges on task completion, a customisable Favorites section, a Trends tab of visual mood summaries, and **guided templates instead of a blank page** `[published, secondary]` ([ScreensDesign](https://screensdesign.com/showcase/journal-mental-health-stoic)).
- **A counter-example worth noting:** the reviewer saw **"Low Data mode" error messages during content loading**, so the graceful-degradation state is unpolished `[published, secondary]`.

### Reconciling the gap

The agent marked as **NOT FOUND**: warm off-white ground, near-black card, ~20px radius, centred light-weight type, uppercase letterspaced eyebrow, outlined-vs-filled pill buttons, 5-slot tab bar, black circular centre FAB, 9 to 10px labels.

**Those are not unsourced. They are `[observed]`**, recorded by the earlier Chrome pass which viewed stoic.'s screens live on Mobbin and described them in [10-mobile-sentiment.md §1](10-mobile-sentiment.md). They carry **single-pass observational confidence**: good enough to design against, not measured to the pixel. The agent was right not to launder them into `[published]`.

**Best-supported answer to the headline question**, combining both passes: with colour removed as a channel, hierarchy is carried by **surface** (one dark card against a light ground, a single figure-ground inversion per screen), **weight and case** (light body against small caps), and **live text state** (the slider label, the streak count) rather than by saturation.

---

## What transfers to a triage feed

1. **Family's delight budget is the governing principle**, and it settles our animation plan. The feed row is the highest-frequency surface, so it gets restraint. The budget goes to inbox-zero, first run, and confirmations.
2. **Habits' allocation model:** pick exactly one interaction (for us, the **swipe to act**) and iterate it to death with synchronised haptic and motion. Ship everything else stock.
3. **WHOOP's published thresholds.** Define urgency bands as **numeric, user-visible rules**, not designer intuition, and reuse the same colours everywhere so the vocabulary is learned once.
4. **Structured's "gaps carry information."** The most novel idea in this set: an empty region states **how much** is empty rather than being blank. Directly portable as a quiet "3 hours clear" or "nothing since 2pm" divider.
5. **Structured's icon-as-identity at small scale.** Icons survive compression better than text, which is what makes their multi-day view work.
6. **Family's direction-matched transitions.** Trivial in Reanimated, disproportionate perceived quality.
7. **Overlay-don't-displace.** Acting on an item should never navigate you away from the list.
8. **Copilot's stock-primitive decision.** When a component's **interaction surface** is large, adopt the platform primitive even if you are custom everywhere else. Their stated reasons were event handling and bug-finding, not rendering.
9. **WHOOP's tap-or-swipe-only disclosure.** Nothing auto-expands.
10. **stoic's live-label feedback.** A control whose own label reports its state, instead of a separate readout.

## What is signature and should not be copied

- **The Habits press-and-hold-longer-than-expected checkbox.** It works because completing a habit happens a handful of times a day and is emotionally loaded. **A triage feed processes dozens of items; forced dwell time on each would be hostile.** Copy the layering technique, not the duration.
- **SceneKit and Blender 3D scenes.** Signature, irrelevant to triage, and not a sane RN target.
- **Shared-letter text morphing.** No RN primitive, and it belongs on a rare irreversible confirmation, not on feed chrome.
- **Family's tray-as-entire-navigation-model.** It exists because crypto flows are short, discrete and consequential. A feed needs persistent list state.
- **stoic's near-total monochrome.** It is a mood instrument for journalling. **Our whole job is urgency differentiation**, so WHOOP's semantic colour is the right model here, not stoic's absence of it.
- **WHOOP's giant hero numeral.** Right for one number per day. A feed has no single hero. Do not import the scale.
- **Structured's duration-proportional block heights.** Correct where duration is the primary attribute. **In a triage feed, row height should encode nothing — uniform rows are what make a list scannable.** This is the one Structured idea that actively does not transfer.

---

## Confidence audit

**Award facts verified, and my earlier framing held on all three:** Habits is a 2022 Delight and Fun **winner** *and* a Visuals and Graphics **finalist**; Structured is a 2026 Inclusivity **finalist**; Copilot Money is a 2024 Innovation **finalist**.

**Corrections made to my own earlier claims**
- WHOOP's "~72pt hero numeral" is an **unmeasured estimate in a marketing blog**, not a spec. I overstated it.
- Copilot's local data storage is documented for **privacy**, not responsiveness. My earlier phrasing was wrong.
- Copilot's animated budget dials and Face ID moment are **unsourced**. I should not have stated them.
- The Structured "neurodivergent users praise the simple layout" **quotation** is unsourced, though the underlying mechanisms are first-party sourced.

**Structural limitation:** this agent viewed zero screenshots and zero video, so every visual-detail claim here is second-hand. Where the earlier Chrome pass *did* view screens (stoic., Mobbin), that is attributed above.

**Where an hour with the actual apps on a device would pay for itself**, in priority order: **stoic.** (nothing verifiable exists publicly; it is a pure screenshot-reading exercise), **WHOOP** (all the interesting specifics are unsourced), and **Structured** (the timeline row anatomy is the actual deliverable and no source describes it). Habits, Family and Copilot are well covered by their primary sources and do not need it.

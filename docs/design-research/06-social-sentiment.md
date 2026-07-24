# Research: what real people say, not just designers

**Date:** 2026-07-24
**Part of:** step 1 research.
**Method:** gathered through the logged-in Chrome session across Reddit, X, YouTube, Dribbble and 21st.dev. Read-only. Nothing was posted, liked or submitted anywhere.

**Read this one first if you only read one.** The other files are practitioner theory. This is the evidence of what actually lands, and it contains the single most important finding of the whole research effort.

> ### ⚠ Medium caveat: mixed web and mobile sources
>
> The critique threads in §2, §3 and §4 are about a **browser-extension side panel, a web financial calculator and 40 websites** respectively. Their findings (one accent, spacing hierarchy, concentric radii, no ragged alignment, 3 to 4 type sizes) are medium-independent and stand.
>
> §1 (the AI-slop inversion), §6 (apps people named), §7 (YouTube) and §8 (the CRED shot) are **already mobile or medium-independent** and stand as written.
>
> §9 (Dribbble) and §10 (21st.dev) were searched with web-leaning queries. **21st.dev in particular is a React web component registry**, so it was always the wrong tool for this. A mobile-only redo of all of it is in [10-mobile-sentiment.md](10-mobile-sentiment.md).

---

## 1. The headline finding: the premium recipe has inverted

Three independent sources, using three different kinds of evidence, converge on the same conclusion.

**A designer built exactly the "premium dark mode" recipe and was rejected by near-unanimous vote.** In [r/UI_Design](https://old.reddit.com/r/UI_Design/comments/1t1rpne/designed_an_institutionalgrade_fintech_os/), someone shipped `#050505` pitch black, frosted-glass cards with blur, and neon cyan accents, and asked to be roasted. The post is net-downvoted with 22 comments.

- Top comment, 45 points: "That looks like all the other thousands of vibe coded tech saas dashboards."
- "AI Slop." / "This just looks vibe coded."
- The sharpest line in the entire research set: **"AI designed interfaces look more and more like what someone would use in a movie, not real life."**
- "It's not bad, it just feels too safe... everything looks polished but nothing really stands out."
- Card soup: "Does it sound like I'm saying card a lot? It's because there's too many cards."
- On the hero number: "Total Balance looks cartoonishly big and bold."
- Density mismatch: "Institutional dashboards are going to be way more data dense... Feels more retail."

**Crucially, the near-black itself was defended, not attacked.** One commenter: "A: It's not pure black. B: They're using cards/elevation." The dark canvas was not the problem. The gradient, glass and neon vocabulary on top of it was.

**Dribbble's own engagement data says the same thing.** The top-performing shots by a wide margin are restrained system shots (UI8's TaskEz at 712k views, Golo's dark dashboard at 565k). A glassmorphic "GLASSLINE" app icon shot sits at 50 likes / 2.8k views. **Restraint outperforms effects by roughly 10 to 20x on the platform that supposedly rewards effects.**

**And [r/web_design](https://old.reddit.com/r/web_design/comments/1uzascg/every_vibecoded_websites_looks_the_same/), 671 points**, names the mechanism:
- The best framing found anywhere: **"You know how bad plastic surgery is really obviously plastic surgery but good plastic surgery isn't?"**
- "Would you like some blue to purple gradient!?" is the single most-named visual tell.
- "AI is trained on the mean and the average so that's what you get."
- The historical parallel: "This is exactly what happened when Bootstrap rose to popularity; every website in the world became a header space with three buckets underneath it."

**The conclusion, and it should shape the entire redesign:** the gradient / glass / neon-on-black vocabulary is now the default output of AI codegen, so **it has flipped from a premium signal into a cheapness signal**. What survived the flip is unglamorous and hard to fake: spacing, a tight type scale, one accent colour, concentric radii, real icons, motion and haptics.

> This is a live risk for us specifically, because we are building with AI assistance. The failure mode is not "the AI writes bad code", it is "the AI writes the average design and the average is now a tell."

---

## 2. The single richest critique thread

["Which is easier on the eyes, cleaner, more premium?"](https://old.reddit.com/r/UI_Design/comments/1sjpn2p/which_is_easier_on_the_eyes_cleaner_more_premium/), 68 comments. Someone asked rounded vs. square. **The consensus was that the radius question was the wrong question.**

**What they said made it cheap:**
- **Saturated accent is the number one offender.** Top comment, 50 points: "Neither is easy on the eyes, the main issue is this very bright saturated green." Independently seconded: "one of the main things that cheapens this design is that green."
- **Ragged left alignment.** "Each row having a different set of elements results in a ragged alignment of the content. You have to actively track your eye on each line."
- **Solid borders everywhere.** "Lighten (or remove) all the borders." Echoed as "just excess use of borders."
- **Cramping.** "They're very cramped (no spacing hierarchy), the font looks cheap and the colour palette clashes."
- **Contrast maxed out.** The counterintuitive one: "There is such thing as contrast being too heavy."
- **Every control visible at once.** "Several icons can be hidden behind hover."

**What they said made it premium:**
- **One radius for everything is wrong.** "You shouldn't apply the same radius to all elements regardless of size, nesting etc." A designer named the concept directly: **concentricity**, "which is another moment of harmony." This is independent confirmation of [the nested-radius research](04-proportion-spacing-icons.md#4-nested-radii-the-rule-we-are-breaking-everywhere) from working designers rather than from a spec.
- Toggles and sliders read correctly only when fully rounded, regardless of the container's radius. Near-unanimous.
- **White space over density.** "Scrolling is normal. Build white space to improve readability."
- **Do not invent.** "Sidebars like this are solved patterns and encourage you to reference how other well-designed apps approach it visually."

---

## 3. The most concrete cheap-signal checklist found

["Why does my financial calculator UI look cheap?"](https://old.reddit.com/r/UI_Design/comments/1sdbv04/why_does_my_financial_calculator_ui_look_cheap/). Small thread, highest density of actionable specifics.

Top comment, 10 points, one line: **"because it looks like an excel file."**

The detailed critique reads as a checklist, and several items hit us directly:
- No alignment across sections.
- **"Your red and green colors are very computer-screen RGB instead of toned appropriately."** Raw sRGB primaries are a cheapness tell.
- Cool/warm clash: blue borders against brown neutrals. "Define a limited color scheme." *(We currently pair a cool slate accent with warm cream and taupe.)*
- "Choose a font that does not feel like an Excel default." *(We ship Menlo.)*
- "Apps don't need a heading and lede paragraph like a document."
- **"Not every field needs to be label: value, which is very dev."**
- "Avoid solid borders to define sections. Try different background shades, card styling."
- Never encode status in colour alone.

---

## 4. The only quantified study

["I looked at about 40 websites this month trying to work out why some feel expensive"](https://old.reddit.com/r/UXDesign/comments/1sl1bek/i_looked_at_about_40_websites_this_month_trying/), r/UXDesign, 88 points. Four measured findings:

1. **Type scale count.** Cohesive sites used **3 or 4 distinct font sizes**. Cluttered ones ran "7, 8, sometimes more." *(We run ten.)*
2. **Section spacing.** Premium sites had **2 to 3x more vertical space between sections**. "Not more content, just more room to breathe."
3. **A trust signal above the fold**, before any feature explanation.
4. **Colour discipline.** "One primary color and everything else was neutral." Cheap-feeling sites ran 4 to 5 competing colours.

**The community reaction is itself the signal.** Designers found this unremarkable: "This is like going into a fire station and saying 'Did you know water can put out fires'." These are treated as settled fundamentals, not opinions.

One veteran named the most common real-world failure: "the most frequent offender I see is lack of white space... clients who want something to look 'premium' but also want to cram in way too much info."

**Honest caveat a commenter raised:** selection bias. The author picked those 40 sites *because* they felt expensive, then found their commonalities.

---

## 5. A warning about the word "premium" itself

["Design not 'Premium' enough"](https://old.reddit.com/r/UXDesign/comments/1tf279e/design_not_premium_enough/), a senior product designer told by leadership his work was not premium enough. This is your exact situation, so it is worth reading carefully.

- The top answer decodes what stakeholders usually mean: "super slick, interactions, big puffy drop shadows, elegant color palettes."
- The warning, from an art director: **"'Premium' was a buzzword people used when they didn't know what they wanted, or how to express it."** The original poster confirms: "When asked what premium means, stakeholders can not explain."
- And the important corrective: **premium is not universally "less."** Density is audience-determined. Chanel is photo-led and sparse because its buyers are not price-focused; Old Navy is dense because its buyers are.

**Why this matters for us:** your manager's "it's not looking premium" is a real signal, but it is a *symptom report*, not a spec. The value of [the audit](00-current-state-audit.md) is that it converts that symptom into ten measurable defects. When the redesign ships, the argument should be made in those terms (ten type steps became six, eleven radii became four, nineteen spacing values became eight) rather than in terms of the word itself.

**And on density specifically:** our audience is engineers looking at a triage feed. The r/UI_Design roast criticised a fintech dashboard for being *insufficiently* dense for its claimed institutional audience. We should not read "premium" as "make it emptier."

---

## 6. Apps people actually named

From ["What are the best mobile apps to study for exceptional UI, animations, and UX?"](https://old.reddit.com/r/UI_Design/comments/1uox0f6) (25 pts) and a curated [r/iosapps list](https://old.reddit.com/r/iosapps/comments/1d0wvjq) (55 pts).

| App | Mentions | What was specifically praised |
|---|---|---|
| **Duolingo** | 3 | Named as a benchmark. Note it was also identified unprompted as the *source* of the "looks basic" problem in another thread. |
| **Spotify** | 3 | No specific technique cited. |
| **Linear** | 2 | The highest-specificity praise in the thread (5 pts): "Linear's kanban board interactions are next level, **the drag and drop feels so precise**." Note: precision of manipulation, not visuals. |
| **Airbnb** | 2 | Benchmark. |
| **CRED** | 1 | Named as an already-studied exemplar. |
| **"Not Boring" apps + Waterllama** | 1 (9 pts, **top comment**) | The top-voted answer. Canonical expressive, animation-heavy, custom-illustrated iOS studio apps. |
| **Flighty** | 1 (3 pts) | Named standalone. |
| **Apple Music / Apple Books** | 1 (2 pts) | First-party craft. |
| **Arc, Amie, Dime, Endel, How We Feel, Sequel, MacroFactor, Gentler Streak, Calmaria, Cosmos, Arena, Stoic, Odio, Literal** | 1 each | The 55-pt curated list. **How We Feel** singled out as "unbelievably unique." |
| **Breathwrk** | 1 | Praised specifically for **haptics over visuals**: "simpler UI than Calmaria's but I personally prefer how they use haptics." |
| **Superhuman** | 1, **mixed** | Qualified: "Design is decent. Could be tastier but regardless, it's extremely utilitarian." A replier disagreed outright: "design isn't the greatest." **Not a clean endorsement.** |

**Not found, flagged honestly:** no Reddit sentiment could be verified for Raycast, Things 3, Revolut, Monzo, Copilot Money, Mercury, Oura, Whoop, Bear or Craft. r/productivity searches returned only sub-20-point, low-signal posts. Rather than pad the table, these are marked as not found. Their inclusion in [the shortlist](07-shortlist.md) rests on primary design-press evidence instead.

**Tools designers named for studying premium UI**, mentioned across three separate threads: **Mobbin**, Screensdesign, Siteinspire, Dribbble/Behance, coolors.co.

---

## 7. YouTube: where the crowd's attention actually is

| Title | Channel | Views | Named techniques |
|---|---|---|---|
| **How I Make Apps FEEL 10x Better (5 Design Secrets)** | Chris Raroque | **202k** | Chapters name all five: **1. Interactions and animations. 2. Custom illustrations. 3. Haptic feedback. 4. Good icons. 5. Elevate your design taste.** Highest-credibility named-technique source found. |
| 7 UI/UX mistakes that SCREAM you're a beginner | Kole Jain | **421k** | Highest-view result overall. Not opened, so the seven are not listed rather than guessed. |
| The UX Psychology Behind Apps People Can't Stop Using | uxpeak | **305k** | Adjacent but well-evidenced: pre-filled forms beat blank; 20% progress beats 0%; **price perception is anchored by what the user saw immediately prior**. |
| Dashboard UI in 8 minutes | Kole Jain | **287k** | Directly our category. |
| **The 7 Color Mistakes that RUIN your UI Designs** | Kole Jain | 77k | Given that saturated accent colour was the number one cheap-signal in every Reddit thread, this is the highest-relevance unwatched item. |
| Mobile App UI's in 8 minutes | Kole Jain | 81k | Chapters: Navigation, Scale, Content, **One Screen One Job**, Gestures, Dynamism. |
| Your AI UI Looks Generic... This Fixes It (DESIGN.md) | Better Stack | 24k | Addresses the AI-generic problem via a `DESIGN.md` spec file. Directly relevant to how we brief AI on this codebase. |

**The consensus read:** view counts cluster around **mistakes** and **colour**, not around gradients or glassmorphism. Raroque's 202k on interactions/haptics/icons plus Jain's 421k on beginner tells puts crowd attention on motion, haptics, icon quality and colour discipline.

**Disclosure worth noting:** Mobbin sponsors three of the top results. Its prominence in "what to study" answers is partly commercial, not purely organic.

---

## 8. Dribbble: the CRED reference, analysed

[The shot you sent](https://dribbble.com/shots/23977904-CRED-Credit-Card-Payments-App-Redesign), by **Girish**, captioned "Day 26: Redesigned CRED app."

**Engagement could not be retrieved.** Dribbble does not render like or view counts on individual shot pages, only in search-grid tiles. No numbers are invented here.

**The visual system, as observed:**

- **True black canvas.** Not dark grey. This is the strongest premium cue in the composition, and it is what licenses everything else to be quiet.
- **Colour lives in exactly one place: the card.** The hero card is an iridescent mint to lavender to pink gradient, a holographic foil metaphor reading as a physical metal object. Two cards behind it peek out in amber and violet. **Everything else is white, grey or black.** This is "one accent, everything else neutral", executed literally.
- **Typography carries the hierarchy, not boxes.** The balance is set very large in a **light or regular weight**, with the supporting line dropping to small with the figure in a muted accent. **Two sizes carry the whole screen.**
- **The weight detail is the important one.** The roasted FinTech OS was criticised for a number that was "cartoonishly big and bold." CRED's number is big but **not bold**. That single weight choice is the difference between the two.
- **Circular icon buttons, borderless.** Four perfect circles, hairline strokes, centred glyphs on black. No fills, no labels, no cards.
- **Concentric radii in practice.** Nav pills are full capsules, the card is a large soft radius, icon buttons are full circles. Three radii, each correct for its size.
- **Zero borders as dividers.** Separation is achieved purely by black space and elevation.
- **Saturation is allowed in exactly one role:** full-bleed promotional tiles in the store screen. **The colour is content, not chrome.**

**The transferable rule:** black chrome, neutral type, one saturated object. The gradient is confined to the single element that represents a physical thing.

> **Our direct analogue:** we have no physical object to be the one saturated element. The candidate is the urgency signal, or the progress heatmap. It should be exactly one of them, not both.

---

## 9. Dribbble shortlist, by validated engagement

| URL | Designer | Likes / Views | Why it reads premium |
|---|---|---|---|
| [TaskEz Productivity App iOS](https://dribbble.com/shots/14630301-TaskEz-Productivity-App-iOS-UI) | UI8 | **2.8k / 712k** | Highest engagement in the entire productivity-iOS search. Dark, restrained, systematised. Our exact category. |
| [Dashboard App Dark Mode](https://dribbble.com/shots/14693218-Dashboard-App-Dark-Mode) | Golo (PRO+) | **1.4k / 565k** | Soft mid-dark surfaces on a light stage rather than pure black. Proves near-black plus elevation reads premium without the pitch-black cliché. |
| [TaskEz, second set](https://dribbble.com/shots/14687754-TaskEz-Productivity-App-iOS-UI) | UI8 | 1.3k / 209k | Companion system shot. |
| [Music App, Identifying Songs](https://dribbble.com/shots/25613891-Music-App-Identifying-Songs) | AmazingUI (PRO+) | 315 / 51.7k | Deep field, single luminous accent, heavy negative space. |
| [Web3 Elite Mobile Banking](https://dribbble.com/shots/27416682-Web3-Elite-Mobile-Banking-App) | Roobinium (PRO+) | 273 / 81.6k | Strong validation despite being in the exact genre Reddit roasted. **The difference: real product imagery grounding the screens, not pure chrome.** |
| [Productivity iOS App](https://dribbble.com/shots/25648601-Productivity-iOS-App) | Fireart Studio (PRO+) | 246 / 51k | **Light** premium. Off-white canvas, generous margins, one accent, large numerals. The counter-example to dark-equals-premium. |
| [Task Management UI Exploration](https://dribbble.com/shots/26851923-Task-Management-App-UI-Exploration) | Zain's Studio (PRO) | 155 / 15.3k | Near-monochrome, single CTA, extreme white space. |
| [Health App, Activity](https://dribbble.com/shots/27054938-Health-App-UI-Design-Activity) | Fahad Ibn Sayeed | 45 / 18.9k | **Dark data-dense cards on a warm bone/cream stage.** A distinctive pairing that avoids the all-black cliché. |
| [Sneaker Inventory Profit](https://dribbble.com/shots/27046313-Sneaker-Inventory-Profit) | Qala Studio (PRO) | 26 / 19.8k | Genuinely dense dark dashboard. **Proves data density and premium are compatible**, which is exactly what the roast said was missing. |
| [Skeuomorphism UI Concept](https://dribbble.com/shots/27571581-Skeuomorphism-UI-Style-Concept) | Hitesh Tapaniya | **9 / 469** | **Low engagement, do not treat as validated.** Listed only because it is the top text match for "premium", which demonstrates the keyword is not a quality proxy. |

**Also observed in-grid:** a luxury-yacht app by Kites Design (169 / 19.5k) using **deep teal + serif type + full-bleed photography**, and a golf app by Admiral Studios (80 / 8.6k) using **dark forest green + gold**. Notable because **neither uses black**. Luxury signalling there comes from deep saturated neutral-adjacent hues plus serif typography.

---

## 10. 21st.dev, and why to treat it as a warning

**Partial access only.** A blocking onboarding modal asking for name and role sits over the site. It is a personal-data form, so it was not filled or submitted. The taxonomy and popularity data were read from the DOM behind the overlay; component detail pages were unreachable.

**Most-installed components:** Container Scroll Animation 7.8k, Scroll media expansion hero 7.7k, Spline Scene 6.7k, Spotlight Card 6.4k, Radial Orbital Timeline 5.9k. Plus a large shader and effect category (Digital Aurora, Liquid Effect, Siri Orb, Siri Wave, Neuro Noise, Silk Aurora) and three categories flagged as new: **ASCII Art, Gradients, Shaders**.

**The honest read:** 21st.dev's popularity data measures **what developers install**, which is close to the opposite of what designers call premium. The top installs are scroll-jacking animations, 3D Spline scenes, spotlight cards, aurora gradients and glowing orbs. That is precisely the vocabulary r/UI_Design roasted as "vibe coded" and "what someone would use in a movie, not real life." Almost all of it is **decorative marketing-page effect, not product-surface component**.

**Use it as a catalog of what is cheap to add, not as a signal of what reads premium.** For a triage app it is close to an anti-reference.

---

## 11. X / Twitter: low yield, reported honestly

Searches for `"looks premium" app design` and `"looks cheap" UI design` returned results dominated by AI-tooling growth threads rather than designer craft discussion. **The search surface is heavily polluted for these exact phrases.**

One genuinely on-point find, from @Dainmercer: "The biggest trap for UI designers moving to Framer? Over-animating. Just because you can make every element bounce and slide, doesn't mean you should. **Premium design is quiet. It doesn't scream for attention.**" The engagement count could not be read, so none is quoted.

That line aligns with the FinTech roast and the "too safe, nothing stands out" critique's inverse. But **one tweet is not a consensus. Treat X as unvalidated for this research.**

---

## 12. Synthesis

### What reads premium, ranked by how often it independently came up

1. **Colour discipline: one accent, everything else neutral.** Every single source. Quantified at 1 primary versus 4 to 5 competing colours. Diagnosed as the root cause in both critique threads. Executed literally in the CRED shot.
2. **Space, at 2 to 3x what feels necessary.** Every source. "White space creates a feeling of prestige."
3. **A tight type scale, 3 to 4 sizes, hierarchy by weight not size.** Cluttered UIs ran 7 to 8+. **Refinement:** large but *light-weight* reads premium; large and bold reads cartoonish.
4. **Motion, micro-interaction and haptics.** Raroque's 202k list leads with interactions and puts haptics third. Reddit independently: "good haptics can make apps literally 'feel' good to use." A Breathwrk user chose it over a better-looking competitor *purely for haptics*. **The most underrated lever in the set, and the hardest for a competitor to screenshot.**
5. **Varied, concentric radii.** Never one radius everywhere. Toggles fully round regardless of container.
6. **Elevation and background-shade separation instead of borders.**
7. **Consistent SVG iconography, one size, one meaning per glyph.**
8. **Restraint.** "Premium design is quiet." Corroborated by Dribbble engagement.
9. **Toned colours, not raw sRGB.** Especially for status and data colours.
10. **Rigid left-edge alignment.** The thing you cannot unsee once named.
11. **Real content and real photography.** Validated shots ground themselves in actual objects; the roasted concept was pure chrome.
12. **Near-black, not pure black.** But note: the black was never the problem. What you put on it decides.

### What reads cheap, ranked

1. **A bright saturated accent colour.** The number one named offender in every critique thread.
2. **Too many hues.** 4 to 8 competing colours, cool/warm clashes, rainbow icon sets.
3. **Cramped spacing with no spacing hierarchy.**
4. **Solid borders everywhere, boxing off sections.** Reads as a form, not a product.
5. **Blue-to-purple gradients, glassmorphism, neon-on-pitch-black.** Now an *active* cheapness signal because it is the AI house style.
6. **Card soup.** Everything wrapped in a card, equal visual weight for unequal information.
7. **The AI tell.** "Contains all information but just feels incoherent, plain and uncreative"; "too safe, nothing really stands out."
8. **Default or system fonts, especially Excel-adjacent.** Font choice alone was enough for multiple people to call a design cheap.
9. **Emoji as iconography.**
10. **Zero radius, or one uniform radius on everything.**
11. **Contrast cranked to maximum.**
12. **Every control visible at once.** No progressive disclosure.
13. **`label: value` everywhere.** "Very dev."
14. **Ragged alignment across rows.**
15. **Colour as the sole status indicator.**

### How our app scores against the cheap list

Nine of fifteen, from [the audit](00-current-state-audit.md):

| Cheap signal | Us |
|---|---|
| Too many hues | Yes. Six pastel roundel tints, plus accent, plus urgent, on cream. |
| Cramped, no spacing hierarchy | Yes. Nineteen ad-hoc spacing values, no ratio between levels. |
| Solid borders boxing off sections | Yes. Box-in-box on every screen. |
| Card soup | Yes. Three equal-weight tiles plus nested cards. |
| Default / Excel-adjacent font | Yes. Menlo. |
| One uniform radius, or unmanaged radii | Yes. Eleven radii, unmanaged concentricity. |
| `label: value` "very dev" | Yes. The stat tiles are literally value-over-label. |
| Colour as sole status indicator | Partly. The tier pip is colour-only. |
| Type scale count | Yes. Ten sizes where 3 to 4 is the premium range. |
| Saturated accent | **No.** Our accent is already muted. |
| Blue-purple gradient / glass / neon | **No.** Explicitly banned in our spec, and correctly so. |

**The encouraging read:** we do not have the two failures that are hardest to recover from, because the accent restraint and the anti-gradient ban were already right. The nine we do have are all systematisable, which is exactly what [step 2](00-current-state-audit.md#8-what-this-audit-does-not-decide) is for.

---

## Process notes

- No page read contained text addressed to an AI agent or attempted to give instructions. Nothing on any page was acted upon as a directive.
- Mobbin sponsors three of the top-ranked YouTube results, so its prominence is partly commercial.
- **Screenshots could not be saved to disk.** The browser tool returned in-session image IDs rather than filesystem paths. Rather than guess at paths, every reference above is cited by its stable URL so it can be re-opened directly.

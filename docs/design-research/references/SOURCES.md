# Reference screenshots: sources and attribution

**Date acquired:** 2026-07-24
**Purpose:** internal design reference for the premium-UI redesign. Not redistributed, not published, not used in any product surface.

All images are **App Store marketing screenshots**, publicly listed by their respective developers, downloaded from Apple's own CDN via each app's public App Store listing. **Copyright remains with each developer.** Each app's icon is included at `icon.jpg` for identification only.

**Every image has been downscaled to 640px wide and re-encoded as JPEG** (133 MB down to 7.2 MB) because full-resolution third-party assets do not belong in a git repository. The originals are re-fetchable from the listings below.

## How to re-fetch at full resolution

```
https://apps.apple.com/<storefront>/app/id<id>
```

The page is JS-rendered, so the iTunes lookup API (`https://itunes.apple.com/lookup?id=<id>&country=<c>`) works for some apps and returns empty `screenshotUrls` for others. For the rest, render the page and read `picture source[srcset]`. Rewriting the trailing size segment of an `mzstatic` URL to `/2000x0w.png` returns the **native source resolution**, verified as not an upscale.

## The apps

| Folder | App | Developer | ID | Store | Shots | Native px |
|---|---|---|---|---|---|---|
| `things3` | Things 3 | Cultured Code GmbH & Co. KG | 904237743 | us | 5 | 1290x2796 |
| `flighty` | Flighty, Live Flight Tracker | Flighty LLC | 1358823008 | us | 6 | 1242x2688 |
| `halide` | Halide Mark III, Pro Camera | Lux Optics Incorporated | 885697368 | us | 6 | 1242x2208 |
| `sequel` | Sequel, Media Tracker | Eventide Studio Ltd | 1630746993 | us | 6 | 1290x2796 |
| `gentlerstreak` | Gentler Streak Workout Tracker | Gentler Stories d.o.o. | 1576857102 | us | 6 | 1290x2796 |
| `structured` | Structured, Daily Planner | unorderly GmbH | 1499198946 | us | 5 | 1284x2778 |
| `notboring-habits` | (Not Boring) Habits | Not Boring Software LLC | 1593891243 | us | 6 | 1284x2778 |
| `whoop` | WHOOP | Whoop Incorporated | 933944389 | us | 6 | 1284x2778 |
| `copilot-money` | Copilot, Track & Budget Money | Copilot Money, Inc. | 1447330651 | us | 6 | 1284x2778 |
| `stoic` | stoic. journal & mental health | Stoic app inc. | 1312926037 | us | 6 | 1242x2208 |
| `darknoise` | Dark Noise, Ambient Sounds | Dark Noise LLC | 1465439395 | us | 6 | 1242x2208 |
| `timepage` | Timepage, Calendar Planner | Bonobo Pte Ltd | 989178902 | us | 6 | 1242x2208 |
| `streaks` | Streaks | Crunchy Bagel Pty Ltd | 963034692 | us | 6 | 1320x2868 |
| `nubank` | Nubank: Conta, Cartão e mais | NU PAGAMENTOS S/A | 814456780 | **br** | 6 | 1242x2208 |
| `cred` | CRED: Credit Cards, Bills, UPI | Dreamplug Technologies Private Limited | **1428580080** | **in** | 6 | 1242x2688 |
| `family` | Family, Crypto Wallet | LFE, Inc. (family.co) | **1606779267** | us | 6 | 1242x2208 |

## Two identification corrections worth recording

- **CRED.** The US App Store's "CRED" (id `1393703565`) is **cred.ai, an unrelated US company**. The Indian fintech is id **`1428580080`** on the **IN** storefront, seller **Dreamplug Technologies**. An earlier guess of `1168717449` returns nothing. Confirmed against the rendered listing.
- **Family.** id **`1606779267`**, seller **LFE, Inc.**, verified via `sellerUrl` resolving to family.co rather than by name matching alone.

## Read this before measuring anything from these files

**These are marketing frames, not raw screen captures.** Nearly every app composites its screens inside a device bezel with a caption band above, and each vendor uses its own template, so the bezel inset differs per app.

**Consequences:**

- **Colour sampling is reliable** once the frame is cropped away, and is the basis of [15-measured-palettes.md](../15-measured-palettes.md).
- **Size measurement is not reliable.** Converting pixels to points requires knowing the exact inner-screen rect, which differs per vendor, giving roughly ±10% error. **No size, spacing, radius or type value in any teardown file was derived from these images.** Where a teardown states a layout number, it comes from published source code (CRED) or a platform spec, never from these screenshots.
- **Device scale varies across the set**, which matters if anyone does attempt measurement: 1242x2208 is 414x736pt, 1242x2688 is 414x896pt, 1284x2778 is 428x926pt, 1290x2796 is 430x932pt, and 1320x2868 is 440x956pt, all at 3x.
- `things3` and `structured` publish only **5** iPhone screenshots each. That is their full published set, not a collection failure.

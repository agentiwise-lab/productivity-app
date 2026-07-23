# Design System (locked)

These tokens are the contract for the mobile UI. Implement against them, do not invent new values.
Reference render: [mockups/screens.html](mockups/screens.html).

## Direction

- **Concept:** an instrument panel, not a consumer social app. Dense with signal, calm, precise.
- **Feeling:** a serious work tool you trust to be quiet unless it matters.

## Colour tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `paper` | `#F6F7F9` | `#0B0E12` | App background |
| `surface` | `#FFFFFF` | `#151920` | Cards, sheets, bars |
| `sunken` | `#EEF0F4` | `#10141A` | Insets, glyph tiles, wells |
| `ink` | `#14171C` | `#E7EAEF` | Primary text |
| `ink-2` | `#454B57` | `#A7AEBB` | Secondary text |
| `ink-3` | `#79808E` | `#727A88` | Metadata, captions |
| `hairline` | `#E2E5EA` | `#222831` | Dividers |
| `hairline-2` | `#D3D8DF` | `#2C333E` | Borders, chips |
| `accent` | `#0E5C4B` | `#3FA98F` | Interactive, active tab, primary button |
| `accent-soft` | `#E1EFEA` | `#12241F` | Active tab fill |
| `signal` | `#B4530F` | `#E0913F` | **Urgency only** |
| `signal-soft` | `#F9E8D9` | `#2A1C11` | Urgent chip fill |

**Colour rules (non-negotiable):**
- `signal` marks **only** "this needs you now". Never decorative, never a brand colour.
- Action types (Review/Approve/Reply/Decide/FYI) are **not** colour-coded. They are mono uppercase chips. This keeps scanning fast and avoids tag soup.
- Neutrals carry a cool blue bias on purpose. Do not substitute pure greys.

## Type

- **UI:** `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, sans-serif`
- **Data / metadata / labels:** `ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace`
- The mono pairing is the signature. All repo refs, counts, timestamps, channel names, section labels and chips are mono.
- Numbers in columns use `font-variant-numeric: tabular-nums`.

| Role | Size | Notes |
|---|---|---|
| Screen title | 20 | tracking `-0.02em` |
| Detail title | 17 | tracking `-0.016em`, `text-wrap: balance` |
| Body / row title | 13.5 | line-height 1.38, clamp 2 lines |
| Metadata | 10 to 11 | mono |
| Section label | 10 | mono, uppercase, tracking `0.11em` |
| Stat value | 21 | mono, tabular |

## Shape and space

- Radii: cards `10px`, buttons `9px`, chips `5–6px`, glyph tiles `7px`. Not everything is pill-shaped.
- Row padding `11px 18px`. Section header `15px 18px 7px`.
- Dividers are 1px hairlines, never shadows, inside lists.

## Explicitly banned (these read as AI-generated)

- Lavender or violet accents, purple to blue gradients
- Glassmorphism, blur panels, glowing borders, gradient orbs
- Coloured left-border/accent rail on rounded cards
- Emoji as section markers or icons
- Inter as the default face
- Badge-above-headline hero pattern, everything centered
- Rounded-everything at a single large radius

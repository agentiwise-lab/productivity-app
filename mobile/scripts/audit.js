/**
 * The design-system audit, run against the built app.
 *
 * This is the check that validated the mockup, pointed at the real thing.
 * Reading the code will not catch what it catches: run against the mockup
 * alone it found a class-name collision putting 64px of margin on every
 * secondary button, a bloom bright enough to make its own caption unreadable,
 * three chips whose text colour inverted in light mode, two fills below AA and
 * a sparkline rounded into beads. Run against the app it found a feed card that
 * did not fill the screen, two gradients whose stop colours were not colours,
 * and a name rendered at 34pt that was a UUID.
 *
 * Usage: `npm run web`, then paste this into the browser console and call
 * `__audit()` on each tab, in both appearances.
 */

(() => {
  /** The six category hues in both modes. Nothing else may be coloured. */
  const HUES = [
    '255,107,95', '99,228,194', '171,127,248', '242,179,102', '127,166,217', '201,183,154',
    '204,68,50', '13,129,103', '113,68,204', '150,99,31', '62,110,168', '110,90,64',
  ];
  /** Brand marks keep their own colours. One of exactly two exemptions. */
  const BRAND = ['171,127,248', '54,197,240', '94,106,210', '234,67,53', '66,133,244'];

  /** The spacing scale, the two OS insets, and the fixed component heights. */
  const SPACING = new Set([
    0, 4, 8, 12, 16, 24, 32, 48, 96,
    54, 34, // the two OS insets
    70,     // 54 + 16: the feed card's body, which bleeds under the status bar
    2,      // (51 - 27) / 2 and (32 - 28) / 2: control insets, derived not chosen
  ]);
  const TYPE = new Set([11, 13, 15, 17, 22, 34, 56]);
  const RADII = new Set([0, 2, 4, 8, 12, 16, 999]);

  const triples = (value) =>
    (String(value).match(/(\d+),\s*(\d+),\s*(\d+)/g) || []).map((s) => s.replace(/\s/g, ''));
  /**
   * The neutral ladders, listed rather than detected. Light mode's neutrals are
   * a sage teal, so "is it grey" reported every one of them as a stray colour.
   */
  const NEUTRALS = [
    '12,11,10', '21,19,17', '29,26,23', '38,34,30', '46,42,38', '59,53,47',
    '87,80,74', '145,138,129', '167,159,151', '245,241,236', '255,253,249',
    '220,230,229', '234,241,240', '242,247,246', '203,218,217', '191,208,207',
    '168,190,189', '134,160,159', '71,96,95', '62,84,83', '18,32,31',
    '255,255,255', '0,0,0',
  ];

  /** WCAG relative luminance, on the sRGB curve rather than a plain average. */
  const luminance = (triple) => {
    const [r, g, b] = triple.split(',').map(Number).map((v) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const ratio = (a, b) => {
    const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m);
    return (x + 0.05) / (y + 0.05);
  };

  /**
   * The nearest *opaque* ancestor, which is what the text actually sits on.
   * A 4% lift is not a background: treating one as the backdrop reported the
   * `why` block's body copy at 1.0:1 against near-black.
   */
  const backdrop = (element) => {
    for (let node = element; node; node = node.parentElement) {
      const match = getComputedStyle(node).backgroundColor.match(/rgba?\(([^)]+)\)/);
      if (!match) continue;
      const parts = match[1].split(',').map((s) => parseFloat(s));
      if (parts.length < 4 || parts[3] >= 0.9) {
        return parts.slice(0, 3).map(Math.round).join(',');
      }
    }
    return null;
  };

  /** A horizontally scrollable ancestor legitimately extends past the fold. */
  const inScroller = (element) => {
    for (let node = element; node; node = node.parentElement) {
      const overflow = getComputedStyle(node).overflowX;
      if (overflow === 'auto' || overflow === 'scroll') return true;
    }
    return false;
  };

  window.__audit = () => {
    const found = {
      strayColours: {},
      offScaleSpacing: {},
      offRampRadii: {},
      offScaleType: {},
      outsetShadows: 0,
      controlsUnder28: {},
      pastTheFold: {},
      contrastBelowAA: {},
    };
    const note = (bucket, key) => {
      found[bucket][key] = (found[bucket][key] || 0) + 1;
    };

        // `body div *` rather than `#root *`: every Modal in the app renders into
    // its own portal outside the root, so scoping to it skipped every sheet.
    for (const element of document.querySelectorAll('body div, body div *')) {
      const style = getComputedStyle(element);
      const box = element.getBoundingClientRect();
      if (style.display === 'none' || box.width === 0 || style.visibility === 'hidden') continue;

      for (const value of [style.color, style.backgroundColor, style.backgroundImage,
                           style.fill, style.stroke, style.borderTopColor]) {
        for (const triple of triples(value)) {
          if (!HUES.includes(triple) && !BRAND.includes(triple) && !NEUTRALS.includes(triple)) {
            note('strayColours', triple);
          }
        }
      }

      for (const key of ['paddingTop', 'paddingBottom', 'paddingLeft', 'paddingRight',
                         'marginTop', 'marginBottom', 'columnGap', 'rowGap']) {
        const value = parseFloat(style[key]);
        if (value && !SPACING.has(value)) note('offScaleSpacing', `${key}=${value}`);
      }

      const corner = parseFloat(style.borderTopLeftRadius);
      if (corner && !RADII.has(corner)) note('offRampRadii', String(corner));

      const leaf = ![...element.childNodes].some((n) => n.nodeType === 1);
      const text = element.textContent.trim();
      if (leaf && text) {
        const size = parseFloat(style.fontSize);
        if (!TYPE.has(size)) note('offScaleType', `${size}: ${text.slice(0, 24)}`);
        const bg = backdrop(element);
        if (bg) {
          const pair = ratio(triples(style.color)[0], bg);
          if (pair < 4.5) note('contrastBelowAA', `${pair.toFixed(1)}: ${text.slice(0, 30)}`);
        }
      }

      if (style.boxShadow !== 'none' && !style.boxShadow.includes('inset')) {
        found.outsetShadows += 1;
      }

      if (element.getAttribute('role') === 'button' || element.getAttribute('role') === 'tab') {
        if (box.height > 0 && box.height < 28) note('controlsUnder28', String(Math.round(box.height)));
      }

      if (box.right > window.innerWidth + 1 && !inScroller(element)) {
        note('pastTheFold', `right=${Math.round(box.right)}`);
      }
    }

    return found;
  };

  return 'audit ready: call __audit()';
})();

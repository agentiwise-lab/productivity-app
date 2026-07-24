/**
 * The line under a row's title.
 *
 * Normally the model's summary: what this actually asks of you. But a tier the
 * rules settle on their own never reaches the model, so Linear issues carrying
 * a priority or a due date had no second line at all while every email had one.
 * The row looked broken rather than merely unclassified.
 *
 * The item's own text is the fallback. An issue description or the first line
 * of a message says less than a written summary, but it says something, and
 * every row keeps the same shape.
 */
export function subtext(row: {
  summary?: string | null;
  body?: string | null;
}): string | null {
  const summary = row.summary?.trim();
  if (summary) return summary;

  const body = row.body?.trim();
  if (!body) return null;

  // First line with actual words in it. Linear descriptions open with a
  // markdown heading, so the raw first line renders as "## V1 Unit 5" on a card
  // that is already showing that title.
  const first = body
    .split('\n')
    .map((line) =>
      line
        .trim()
        .replace(/^#{1,6}\s*/, '')       // heading
        .replace(/^[-*+]\s+/, '')        // bullet
        .replace(/^>\s*/, '')            // quote
        // Inline markup, which is markup we are never going to render. A link
        // left whole put a hundred characters of URL in the middle of a
        // sentence: keep the words, drop the address.
        .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')  // link
        .replace(/`([^`]+)`/g, '$1')                 // code span
        .replace(/\*\*([^*]+)\*\*/g, '$1')          // bold
        .replace(/\s+/g, ' ')
        .trim(),
    )
    .find((line) => line.length > 0);
  return first ? first.slice(0, 140) : null;
}

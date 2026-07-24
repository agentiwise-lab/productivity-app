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
/**
 * One line of markdown as the words it was carrying.
 *
 * We are never going to render markdown: there is no renderer in the app and a
 * feed row is not a document. So the syntax comes off and the text stays. A
 * link left whole put a hundred characters of URL in the middle of a sentence.
 */
function strip(line: string): string {
  return line
    .trim()
    .replace(/^#{1,6}\s*/, '') // heading
    .replace(/^[-*+]\s+/, '') // bullet
    .replace(/^>\s*/, '') // quote
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // link
    .replace(/`([^`]+)`/g, '$1') // code span
    .replace(/\*\*([^*]+)\*\*/g, '$1') // bold
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * A whole body, for the detail sheet, which shows all of it.
 *
 * Paragraph breaks survive because they are the only structure worth keeping
 * without a renderer; every other mark is dropped. Untreated, a Linear issue
 * opened with a literal `## What to build` and its code spans still wearing
 * their backticks, which is the app showing its input rather than its content.
 */
export function readable(raw?: string | null): string | null {
  const body = raw?.trim();
  if (!body) return null;
  return (
    body
      // Fenced code cannot be laid out as prose and reads as noise unfenced.
      .replace(/```[\s\S]*?```/g, '')
      .split(/\n{2,}/)
      .map((block) => block.split('\n').map(strip).filter(Boolean).join(' '))
      .filter(Boolean)
      .join('\n\n') || null
  );
}

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
  const first = body.split('\n').map(strip).find((line) => line.length > 0);
  return first ? first.slice(0, 140) : null;
}

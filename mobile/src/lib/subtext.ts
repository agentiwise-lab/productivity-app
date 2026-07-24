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
 * HTML entities as their characters.
 *
 * Mail arrives escaped for a web client it is never going to be shown in, so an
 * apostrophe reaches the phone as `&#39;` and a quotation mark as `&quot;`. The
 * later list decodes on the server; the feed body and summary do not, so it is
 * done here where both of them are read.
 */
const NAMED: Record<string, string> = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  nbsp: ' ',
};

export function decodeEntities(input: string): string {
  return input.replace(/&(#\d+|#x[0-9a-f]+|[a-z]+);/gi, (whole, code: string) => {
    if (code[0] === '#') {
      const n =
        code[1] === 'x' || code[1] === 'X'
          ? parseInt(code.slice(2), 16)
          : parseInt(code.slice(1), 10);
      return Number.isFinite(n) ? String.fromCodePoint(n) : whole;
    }
    return NAMED[code.toLowerCase()] ?? whole;
  });
}

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
  const body = decodeEntities(raw?.trim() || '');
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

/** The message itself, one line, decoded and de-marked. */
export function oneLine(raw?: string | null): string | null {
  const body = decodeEntities(raw?.trim() || '');
  if (!body) return null;
  const first = body.split('\n').map(strip).find((line) => line.length > 0);
  return first ? first.slice(0, 140) : null;
}

export function subtext(row: {
  source?: string;
  summary?: string | null;
  body?: string | null;
}): string | null {
  // On a mail or a chat message the message *is* the content, so the card
  // shows it rather than the model's paraphrase of it. The paraphrase reads as
  // the app talking about the item instead of showing it, and the reason block
  // below already carries the "why". For an issue or a PR the body is a wall of
  // markdown, so there the one-line summary is the better line.
  const conversational = row.source === 'gmail' || row.source === 'slack';
  if (conversational) {
    return oneLine(row.body) ?? (row.summary ? decodeEntities(row.summary.trim()) : null);
  }
  const summary = row.summary?.trim();
  if (summary) return decodeEntities(summary);
  return oneLine(row.body);
}

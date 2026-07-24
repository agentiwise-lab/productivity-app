/**
 * Reading server-sent events on both React Native and the web.
 *
 * `fetch` cannot do this here: React Native's implementation resolves the whole
 * body before handing it over, so a streaming response arrives as one lump at
 * the end and the point is lost. `XMLHttpRequest` fires `onprogress` as bytes
 * land on both platforms, so the parser works off the growing `responseText`.
 *
 * The frames are plain SSE: `event: <name>` then `data: <json>`, separated by a
 * blank line. Only complete frames are consumed, and the offset is carried so a
 * frame split across two progress events is not parsed twice or dropped.
 */

export interface StreamHandle {
  cancel: () => void;
}

export function streamEvents<T>({
  url,
  headers,
  onBatch,
  onDone,
  onError,
}: {
  url: string;
  headers: Record<string, string>;
  onBatch: (rows: T[]) => void;
  onDone: () => void;
  onError: (message: string) => void;
}): StreamHandle {
  const xhr = new XMLHttpRequest();
  let consumed = 0;
  let finished = false;

  const finish = () => {
    if (finished) return;
    finished = true;
    onDone();
  };

  /** Parse every complete frame that has arrived since the last call. */
  const drain = () => {
    const text: string = xhr.responseText ?? '';
    // A frame ends at a blank line. Anything after the last one is a partial
    // frame still being written, so it waits for the next progress event.
    let boundary = text.indexOf('\n\n', consumed);
    while (boundary !== -1) {
      const frame = text.slice(consumed, boundary);
      consumed = boundary + 2;
      boundary = text.indexOf('\n\n', consumed);

      let name = 'message';
      const data: string[] = [];
      for (const line of frame.split('\n')) {
        if (line.startsWith('event:')) name = line.slice(6).trim();
        else if (line.startsWith('data:')) data.push(line.slice(5).trim());
      }
      if (!data.length) continue;

      if (name === 'done') {
        finish();
        return;
      }
      try {
        const parsed = JSON.parse(data.join('\n')) as T[];
        if (Array.isArray(parsed) && parsed.length) onBatch(parsed);
      } catch {
        // A malformed frame loses that batch, not the stream.
      }
    }
  };

  xhr.open('GET', url, true);
  Object.entries({ Accept: 'text/event-stream', ...headers }).forEach(([k, v]) =>
    xhr.setRequestHeader(k, v),
  );
  xhr.onprogress = drain;
  xhr.onload = () => {
    drain();
    finish();
  };
  xhr.onerror = () => {
    if (finished) return;
    finished = true;
    onError("Can't reach the backend.");
  };
  // Cancelling fires onabort, not onerror: leaving the screen is not a failure.
  xhr.onabort = () => {
    finished = true;
  };
  xhr.send();

  return {
    cancel: () => {
      if (!finished) xhr.abort();
    },
  };
}

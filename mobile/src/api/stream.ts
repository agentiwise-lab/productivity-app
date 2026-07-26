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
  onUnauthorized,
}: {
  url: string;
  headers: Record<string, string>;
  onBatch: (rows: T[]) => void;
  onDone: () => void;
  onError: (message: string) => void;
  /**
   * Called when the stream completes with a 401. A stale access token is the
   * common cause (the token was minted before the screen mounted). The handler
   * runs the single-flight refresh and returns fresh auth headers, or null when
   * the session is truly gone. On fresh headers the stream reconnects once. A
   * 401 response carries no SSE frames, so nothing was emitted yet and the
   * reconnect starts clean — no duplicate rows.
   */
  onUnauthorized?: () => Promise<Record<string, string> | null>;
}): StreamHandle {
  let xhr = new XMLHttpRequest();
  let consumed = 0;
  let finished = false;
  let cancelled = false;

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

  const connect = (currentHeaders: Record<string, string>, allowRetry: boolean) => {
    xhr = new XMLHttpRequest();
    consumed = 0;
    xhr.open('GET', url, true);
    Object.entries({ Accept: 'text/event-stream', ...currentHeaders }).forEach(
      ([k, v]) => xhr.setRequestHeader(k, v),
    );
    xhr.onprogress = drain;
    xhr.onload = () => {
      if (xhr.status === 401 && allowRetry && onUnauthorized) {
        // Do not finish: refresh the token, then reconnect once with it.
        onUnauthorized()
          .then((fresh) => {
            if (cancelled || finished) return;
            if (fresh) connect(fresh, false);
            else {
              finished = true;
              onError('Your session expired. Sign in again.');
            }
          })
          .catch(() => {
            if (cancelled || finished) return;
            finished = true;
            onError('Your session expired. Sign in again.');
          });
        return;
      }
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
  };

  connect(headers, true);

  return {
    cancel: () => {
      cancelled = true;
      if (!finished) xhr.abort();
    },
  };
}

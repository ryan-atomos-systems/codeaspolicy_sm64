// Small LRU pages; late responses from a different session are never displayed.
export class OracleData {
  constructor(run, session) {
    this.run = run;
    this.session = session;
    this.pages = new Map();
    this.pending = new Map();
    this.size = 24;
    this.total = Infinity;
    this.closed = false;
    this.aborts = new Set();
  }
  close() {
    this.closed = true;
    this.aborts.forEach((c) => c.abort());
    this.pages.clear();
  }
  async page(start) {
    if (this.pages.has(start)) {
      const page = this.pages.get(start);
      this.pages.delete(start);
      this.pages.set(start, page);
      return page;
    }
    if (this.pending.has(start)) return this.pending.get(start);
    const abort = new AbortController();
    this.aborts.add(abort);
    const query = new URLSearchParams({
      run: this.run,
      session: this.session,
      start,
      count: this.size,
    });
    const promise = fetch(`/api/states?${query}`, { signal: abort.signal })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(
            "Oracle observations are unavailable for this frame.",
          );
        const page = await response.json();
        if (!this.closed) {
          this.total = page.total;
          this.pages.set(start, page);
          while (this.pages.size > 6)
            this.pages.delete(this.pages.keys().next().value);
        }
        return page;
      })
      .finally(() => {
        this.pending.delete(start);
        this.aborts.delete(abort);
      });
    this.pending.set(start, promise);
    return promise;
  }
  async get(index) {
    const start = Math.floor(index / this.size) * this.size;
    const page = await this.page(start);
    if (index - start > this.size / 2 && start + this.size < this.total)
      this.page(start + this.size).catch(() => {});
    return {
      input: index > 0 ? page.observations[index - 1 - page.start] : null,
      output: page.observations[index - page.start],
    };
  }
}

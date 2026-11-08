// Prevent expensive research requests from crowding out login and live quotes.
// The admission slot remains held until the full asynchronous task finishes.
export function capacityGate(maxConcurrent = 1) {
  if (!Number.isInteger(maxConcurrent) || maxConcurrent < 1) throw new Error('Invalid capacity');
  let running = 0;
  return {
    acquire() {
      if (running >= maxConcurrent) return null;
      running++;
      let released = false;
      return () => { if (!released) { released = true; running--; } };
    },
    get active() { return running; },
    get capacity() { return maxConcurrent; }
  };
}

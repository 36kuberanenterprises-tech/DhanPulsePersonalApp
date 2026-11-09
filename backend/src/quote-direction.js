// A factual comparison of a fresh quote to the day's opening price and
// previous close. This is NOT a signal or a replacement for broker candles.
export function quoteDirection(quote, price, feedAgeMs) {
  const fresh = Number.isFinite(feedAgeMs) && feedAgeMs >= -30_000 && feedAgeMs <= 45_000;
  const open = Number(quote?.open);
  const previousClose = Number(quote?.close);
  const valid = fresh && Number.isFinite(price) && price > 0 &&
    Number.isFinite(open) && open > 0 &&
    Number.isFinite(previousClose) && previousClose > 0;
  const reference = { open: Number.isFinite(open) && open > 0 ? open : null,
    previousClose: Number.isFinite(previousClose) && previousClose > 0 ? previousClose : null,
    ageSeconds: Number.isFinite(feedAgeMs) ? Math.max(0, Math.round(feedAgeMs / 1000)) : null };
  if (!valid) return { ...reference, status: 'UNVERIFIED', label: 'Quote direction unavailable',
    detail: fresh ? 'Broker did not provide valid opening and previous closing prices.' :
      'The last broker quote is delayed or has no verified exchange timestamp.',
    tradeCall: false };
  const vsOpenPct = (price / open - 1) * 100;
  const vsClosePct = (price / previousClose - 1) * 100;
  // Both comparisons must agree; small changes are not labelled as a trend.
  const minChangePct = 0.15;
  const status = vsOpenPct >= minChangePct && vsClosePct >= minChangePct ? 'UP' :
    vsOpenPct <= -minChangePct && vsClosePct <= -minChangePct ? 'DOWN' : 'MIXED';
  return { ...reference, vsOpenPct: Number(vsOpenPct.toFixed(2)),
    vsPreviousClosePct: Number(vsClosePct.toFixed(2)), status,
    label: status === 'UP' ? 'UPWARD QUOTE MOVE' : status === 'DOWN' ? 'DOWNWARD QUOTE MOVE' : 'MIXED QUOTE MOVE',
    detail: status === 'UP' ? 'Latest quote is above both the opening price and previous close.' :
      status === 'DOWN' ? 'Latest quote is below both the opening price and previous close.' :
      'Opening price and previous close comparisons do not establish a clear intraday direction.',
    tradeCall: false };
}

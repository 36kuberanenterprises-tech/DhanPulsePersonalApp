package com.dhanpulse.cryptofxnative;

import java.util.Locale;

/**
 * Adaptive multi-strategy decision engine for DhanPulse.
 *
 * The engine does not force a trade. It first classifies the regime, then
 * scores several independent strategy families and applies conflict/quality
 * vetoes. The returned confidence is an internal ranking score, not a
 * probability of profit.
 */
public final class AdaptiveEnsemble {
    private AdaptiveEnsemble() {}

    public static final class Result {
        public final boolean trade;
        public final int dir; // +1 buy, -1 sell
        public final String regime;
        public final String strategy;
        public final int confidence;
        public final double riskAtrMult;
        public final String reason;

        Result(boolean trade, int dir, String regime, String strategy, int confidence,
               double riskAtrMult, String reason) {
            this.trade = trade;
            this.dir = dir;
            this.regime = regime;
            this.strategy = strategy;
            this.confidence = confidence;
            this.riskAtrMult = riskAtrMult;
            this.reason = reason;
        }

        static Result waitResult(String regime, int confidence, String reason) {
            return new Result(false, 0, regime, "WAIT", confidence, 1.0, reason);
        }
    }

    private static final class Candidate {
        final int dir;
        final String name;
        final int score;
        final int threshold;
        final double riskAtr;
        final String reason;
        Candidate(int dir, String name, int score, int threshold, double riskAtr, String reason) {
            this.dir = dir; this.name = name; this.score = score; this.threshold = threshold;
            this.riskAtr = riskAtr; this.reason = reason;
        }
    }

    public static Result evaluate(
            double[] o, double[] h, double[] l, double[] c, double[] v, double[] takerBuy,
            double flow, double book, double fundingRate, double oiChangePct, double spreadBps,
            int bias15, int bias60, int turningDir, int turningScore, boolean turningTrigger) {

        int n = c == null ? 0 : c.length;
        if (n < 60) return Result.waitResult("WARMING UP", 0, "Need more candle history");

        int i = n - 1;
        double price = c[i];
        double atr = atrLast(h, l, c, 14);
        if (!finite(atr) || atr <= 0) return Result.waitResult("DATA CHECK", 0, "ATR unavailable");

        double ema5 = emaLast(c, 5);
        double ema9 = emaLast(c, 9);
        double ema21 = emaLast(c, 21);
        double ema50 = emaLast(c, 50);
        double ema21Prev = emaAt(c, 21, Math.max(21, n - 4));
        double slope21 = finite(ema21Prev) ? ema21 - ema21Prev : 0.0;
        double rsi = rsiLast(c, 14);
        double adx = adxLast(h, l, c, 14);
        double sma20 = mean(c, Math.max(0, n - 20), n);
        double sd20 = std(c, Math.max(0, n - 20), n, sma20);
        double z20 = sd20 > 0 ? (price - sma20) / sd20 : 0.0;
        double priorHigh20 = max(h, Math.max(0, n - 21), n - 1);
        double priorLow20 = min(l, Math.max(0, n - 21), n - 1);
        double priorHigh50 = max(h, Math.max(0, n - 51), n - 1);
        double priorLow50 = min(l, Math.max(0, n - 51), n - 1);
        double volumeRatio = volumeRatio(v, n);
        double takerRatio = takerRatio(v, takerBuy, n);
        double atrRatio = atrRegimeRatio(h, l, c, atr);
        double momentum3 = n >= 4 ? (price - c[n - 4]) / Math.max(atr, 1e-9) : 0.0;
        double candleRange = Math.max(h[i] - l[i], 1e-9);
        double body = Math.abs(c[i] - o[i]);
        double upperWick = h[i] - Math.max(o[i], c[i]);
        double lowerWick = Math.min(o[i], c[i]) - l[i];
        boolean bullishReject = lowerWick / candleRange > 0.42 && c[i] > l[i] + candleRange * 0.55;
        boolean bearishReject = upperWick / candleRange > 0.42 && c[i] < l[i] + candleRange * 0.45;
        boolean displacementUp = c[i] > o[i] && body > atr * 0.65 && c[i] > l[i] + candleRange * 0.70;
        boolean displacementDown = c[i] < o[i] && body > atr * 0.65 && c[i] < l[i] + candleRange * 0.30;
        boolean trendUp = ema5 >= ema9 && ema9 > ema21 && ema21 > ema50 && slope21 > 0 && price > ema21;
        boolean trendDown = ema5 <= ema9 && ema9 < ema21 && ema21 < ema50 && slope21 < 0 && price < ema21;
        boolean breakoutUp = price > priorHigh20 + atr * 0.03;
        boolean breakoutDown = price < priorLow20 - atr * 0.03;
        boolean rangeLike = adx < 18.5 && atrRatio < 1.35;
        boolean extremeVol = atrRatio > 1.85 || candleRange > atr * 2.45;
        boolean deadMarket = atrRatio < 0.58 && adx < 14.0 && volumeRatio < 0.80;
        double vwap = vwap(h, l, c, v);

        String regime;
        if (extremeVol) regime = "EXTREME VOLATILITY";
        else if (breakoutUp && volumeRatio > 1.12) regime = "BREAKOUT UP";
        else if (breakoutDown && volumeRatio > 1.12) regime = "BREAKOUT DOWN";
        else if (trendUp && adx >= 19.0) regime = "TREND UP";
        else if (trendDown && adx >= 19.0) regime = "TREND DOWN";
        else if (rangeLike) regime = "RANGE";
        else regime = "TRANSITION";

        if (finite(spreadBps) && spreadBps > 12.0) {
            return Result.waitResult(regime, 0, "Spread too wide for reliable execution");
        }
        if (deadMarket) return Result.waitResult("LOW ACTIVITY", 0, "Low volatility and weak participation");

        Candidate bestLong = null;
        Candidate bestShort = null;

        // 1. Trend continuation / pullback
        if (trendUp) {
            int s = 57;
            boolean pullback = l[i] <= ema9 + atr * 0.24 && price >= ema9;
            if (adx > 23) s += 7;
            if (pullback) s += 9;
            if (rsi >= 50 && rsi <= 70) s += 5;
            if (finite(vwap) && price > vwap) s += 4;
            s += flowScore(flow, 1, 6) + bookScore(book, 1, 4) + htfScore(bias15, bias60, 1);
            if (takerRatio > 0.53) s += 4;
            if (oiChangePct > 0.03) s += 4;
            if (fundingRate > 0.0007) s -= 5;
            if (priorHigh20 - price < atr * 0.55 && !breakoutUp) s -= 6;
            bestLong = choose(bestLong, new Candidate(1, "TREND PULLBACK", s, 74, 1.00,
                    metrics("trend", adx, volumeRatio, flow, book, bias15, bias60)));
        }
        if (trendDown) {
            int s = 57;
            boolean pullback = h[i] >= ema9 - atr * 0.24 && price <= ema9;
            if (adx > 23) s += 7;
            if (pullback) s += 9;
            if (rsi >= 30 && rsi <= 50) s += 5;
            if (finite(vwap) && price < vwap) s += 4;
            s += flowScore(flow, -1, 6) + bookScore(book, -1, 4) + htfScore(bias15, bias60, -1);
            if (takerRatio < 0.47) s += 4;
            if (oiChangePct > 0.03) s += 4;
            if (fundingRate < -0.0007) s -= 5;
            if (price - priorLow20 < atr * 0.55 && !breakoutDown) s -= 6;
            bestShort = choose(bestShort, new Candidate(-1, "TREND PULLBACK", s, 74, 1.00,
                    metrics("trend", adx, volumeRatio, flow, book, bias15, bias60)));
        }

        // 2. Breakout with participation confirmation
        if (breakoutUp) {
            int s = 58;
            if (volumeRatio > 1.20) s += 8;
            if (atrRatio > 1.02) s += 5;
            if (displacementUp) s += 6;
            s += flowScore(flow, 1, 8) + bookScore(book, 1, 5) + htfScore(bias15, bias60, 1);
            if (oiChangePct > 0.03) s += 5; else if (oiChangePct < -0.08) s -= 5;
            if (takerRatio > 0.55) s += 5;
            if (z20 > 3.1) s -= 8;
            bestLong = choose(bestLong, new Candidate(1, "BREAKOUT", s, 78, 1.25,
                    metrics("breakout", adx, volumeRatio, flow, book, bias15, bias60)));
        }
        if (breakoutDown) {
            int s = 58;
            if (volumeRatio > 1.20) s += 8;
            if (atrRatio > 1.02) s += 5;
            if (displacementDown) s += 6;
            s += flowScore(flow, -1, 8) + bookScore(book, -1, 5) + htfScore(bias15, bias60, -1);
            if (oiChangePct > 0.03) s += 5; else if (oiChangePct < -0.08) s -= 5;
            if (takerRatio < 0.45) s += 5;
            if (z20 < -3.1) s -= 8;
            bestShort = choose(bestShort, new Candidate(-1, "BREAKOUT", s, 78, 1.25,
                    metrics("breakout", adx, volumeRatio, flow, book, bias15, bias60)));
        }

        // 3. Short-horizon mean reversion in non-trending / exhaustion regimes
        if ((rangeLike || extremeVol || "TRANSITION".equals(regime)) && z20 < -1.75 && rsi < 39) {
            int s = 59;
            if (z20 < -2.2) s += 8;
            if (rsi < 32) s += 6;
            if (bullishReject) s += 8;
            if (turningDir == 1) s += Math.min(10, turningScore);
            if (flow > -0.12) s += 4;
            if (book > -0.10) s += 3;
            if (bias15 == -1 && bias60 == -1) s -= 11;
            if (price < priorLow50 && !bullishReject) s -= 7;
            bestLong = choose(bestLong, new Candidate(1, "MEAN REVERSION", s, 80, 0.95,
                    metrics("reversal", adx, volumeRatio, flow, book, bias15, bias60)));
        }
        if ((rangeLike || extremeVol || "TRANSITION".equals(regime)) && z20 > 1.75 && rsi > 61) {
            int s = 59;
            if (z20 > 2.2) s += 8;
            if (rsi > 68) s += 6;
            if (bearishReject) s += 8;
            if (turningDir == -1) s += Math.min(10, turningScore);
            if (flow < 0.12) s += 4;
            if (book < 0.10) s += 3;
            if (bias15 == 1 && bias60 == 1) s -= 11;
            if (price > priorHigh50 && !bearishReject) s -= 7;
            bestShort = choose(bestShort, new Candidate(-1, "MEAN REVERSION", s, 80, 0.95,
                    metrics("reversal", adx, volumeRatio, flow, book, bias15, bias60)));
        }

        // 4. Liquidity sweep / microstructure reversal
        if (turningTrigger && turningDir != 0) {
            int s = 68 + Math.min(14, Math.max(0, turningScore));
            s += flowScore(flow, turningDir, 6) + bookScore(book, turningDir, 4);
            int htf = htfScore(bias15, bias60, turningDir);
            if (htf >= 0) s += Math.min(6, htf); else s += Math.max(-10, htf);
            Candidate x = new Candidate(turningDir, "LIQUIDITY REVERSAL", s, 82, 1.10,
                    metrics("liquidity sweep", adx, volumeRatio, flow, book, bias15, bias60));
            if (turningDir > 0) bestLong = choose(bestLong, x); else bestShort = choose(bestShort, x);
        }

        // 5. Momentum ignition after fresh participation arrives
        if (momentum3 > 0.72 && volumeRatio > 1.08 && (flow > 0.08 || takerRatio > 0.54)) {
            int s = 55;
            if (momentum3 > 1.15) s += 7;
            if (volumeRatio > 1.30) s += 7;
            if (flow > 0.15) s += 8;
            if (book > 0.08) s += 4;
            if (oiChangePct > 0.03) s += 6;
            if (ema5 > ema9) s += 5;
            s += htfScore(bias15, bias60, 1);
            if (z20 > 3.0) s -= 7;
            bestLong = choose(bestLong, new Candidate(1, "MOMENTUM IGNITION", s, 78, 1.15,
                    metrics("momentum", adx, volumeRatio, flow, book, bias15, bias60)));
        }
        if (momentum3 < -0.72 && volumeRatio > 1.08 && (flow < -0.08 || takerRatio < 0.46)) {
            int s = 55;
            if (momentum3 < -1.15) s += 7;
            if (volumeRatio > 1.30) s += 7;
            if (flow < -0.15) s += 8;
            if (book < -0.08) s += 4;
            if (oiChangePct > 0.03) s += 6;
            if (ema5 < ema9) s += 5;
            s += htfScore(bias15, bias60, -1);
            if (z20 < -3.0) s -= 7;
            bestShort = choose(bestShort, new Candidate(-1, "MOMENTUM IGNITION", s, 78, 1.15,
                    metrics("momentum", adx, volumeRatio, flow, book, bias15, bias60)));
        }

        int longScore = bestLong == null ? 0 : bestLong.score;
        int shortScore = bestShort == null ? 0 : bestShort.score;
        Candidate best = longScore >= shortScore ? bestLong : bestShort;
        Candidate opposite = best == bestLong ? bestShort : bestLong;
        if (best == null) return Result.waitResult(regime, 0, "No strategy has a valid setup");

        // Conflict veto: both sides strong means transition/noise rather than edge.
        if (opposite != null && opposite.score >= opposite.threshold - 4 && Math.abs(best.score - opposite.score) < 9) {
            return Result.waitResult(regime, Math.max(best.score, opposite.score), "Conflicting high quality long and short setups");
        }

        int adjusted = best.score;
        if (finite(spreadBps) && spreadBps > 5.0) adjusted -= 5;
        if (extremeVol && !"LIQUIDITY REVERSAL".equals(best.name) && !"BREAKOUT".equals(best.name)) adjusted -= 4;
        if (adjusted < best.threshold) {
            return Result.waitResult(regime, adjusted, best.name + " setup below quality threshold");
        }

        return new Result(true, best.dir, regime, best.name, Math.min(99, adjusted), best.riskAtr,
                best.reason + " · threshold " + best.threshold);
    }

    private static Candidate choose(Candidate a, Candidate b) {
        return a == null || b.score > a.score ? b : a;
    }

    private static int flowScore(double flow, int dir, int max) {
        double x = flow * dir;
        if (x > 0.22) return max;
        if (x > 0.12) return Math.max(1, max - 2);
        if (x > 0.05) return Math.max(1, max - 4);
        if (x < -0.20) return -max;
        if (x < -0.10) return -Math.max(2, max - 2);
        return 0;
    }

    private static int bookScore(double book, int dir, int max) {
        double x = book * dir;
        if (x > 0.20) return max;
        if (x > 0.10) return Math.max(1, max - 1);
        if (x > 0.04) return Math.max(1, max - 3);
        if (x < -0.20) return -max;
        return 0;
    }

    private static int htfScore(int b15, int b60, int dir) {
        int s = 0;
        if (b15 == dir) s += 5; else if (b15 == -dir) s -= 5;
        if (b60 == dir) s += 6; else if (b60 == -dir) s -= 7;
        return s;
    }

    private static String metrics(String label, double adx, double vol, double flow, double book, int b15, int b60) {
        return String.format(Locale.US, "%s · ADX %.1f · vol %.2fx · flow %.2f · book %.2f · 15m %d · 1h %d",
                label, adx, vol, flow, book, b15, b60);
    }

    private static boolean finite(double x) { return !Double.isNaN(x) && !Double.isInfinite(x); }

    private static double emaLast(double[] a, int p) { return emaAt(a, p, a.length - 1); }
    private static double emaAt(double[] a, int p, int endIndex) {
        if (a == null || endIndex + 1 < p || endIndex >= a.length) return Double.NaN;
        double v = 0;
        for (int i = 0; i < p; i++) v += a[i];
        v /= p;
        double k = 2.0 / (p + 1.0);
        for (int i = p; i <= endIndex; i++) v = a[i] * k + v * (1.0 - k);
        return v;
    }

    private static double rsiLast(double[] a, int p) {
        if (a.length <= p) return Double.NaN;
        double g = 0, loss = 0;
        for (int i = 1; i <= p; i++) {
            double d = a[i] - a[i - 1];
            if (d >= 0) g += d; else loss -= d;
        }
        double ag = g / p, al = loss / p;
        double out = al == 0 ? 100 : 100 - 100 / (1 + ag / al);
        for (int i = p + 1; i < a.length; i++) {
            double d = a[i] - a[i - 1];
            ag = (ag * (p - 1) + Math.max(d, 0)) / p;
            al = (al * (p - 1) + Math.max(-d, 0)) / p;
            out = al == 0 ? 100 : 100 - 100 / (1 + ag / al);
        }
        return out;
    }

    private static double atrLast(double[] h, double[] l, double[] c, int p) {
        if (c.length < p + 1) return Double.NaN;
        double[] tr = new double[c.length];
        tr[0] = h[0] - l[0];
        for (int i = 1; i < c.length; i++) tr[i] = Math.max(h[i] - l[i], Math.max(Math.abs(h[i] - c[i - 1]), Math.abs(l[i] - c[i - 1])));
        double v = 0;
        for (int i = 0; i < p; i++) v += tr[i];
        v /= p;
        for (int i = p; i < tr.length; i++) v = (v * (p - 1) + tr[i]) / p;
        return v;
    }

    private static double atrRegimeRatio(double[] h, double[] l, double[] c, double currentAtr) {
        int n = c.length;
        int from = Math.max(1, n - 55);
        double sum = 0; int count = 0;
        for (int i = from; i < n; i++) {
            double tr = Math.max(h[i] - l[i], Math.max(Math.abs(h[i] - c[i - 1]), Math.abs(l[i] - c[i - 1])));
            sum += tr; count++;
        }
        double baseline = count > 0 ? sum / count : currentAtr;
        return baseline > 0 ? currentAtr / baseline : 1.0;
    }

    private static double adxLast(double[] h, double[] l, double[] c, int p) {
        int n = c.length;
        if (n < p * 2 + 2) return Double.NaN;
        double trS = 0, plusS = 0, minusS = 0;
        double[] dx = new double[n];
        int dxCount = 0;
        for (int i = 1; i < n; i++) {
            double up = h[i] - h[i - 1];
            double down = l[i - 1] - l[i];
            double plus = up > down && up > 0 ? up : 0;
            double minus = down > up && down > 0 ? down : 0;
            double tr = Math.max(h[i] - l[i], Math.max(Math.abs(h[i] - c[i - 1]), Math.abs(l[i] - c[i - 1])));
            if (i <= p) {
                trS += tr; plusS += plus; minusS += minus;
                if (i < p) continue;
            } else {
                trS = trS - trS / p + tr;
                plusS = plusS - plusS / p + plus;
                minusS = minusS - minusS / p + minus;
            }
            double pdi = trS > 0 ? 100.0 * plusS / trS : 0;
            double mdi = trS > 0 ? 100.0 * minusS / trS : 0;
            double denom = pdi + mdi;
            dx[i] = denom > 0 ? 100.0 * Math.abs(pdi - mdi) / denom : 0;
            dxCount++;
        }
        if (dxCount < p) return Double.NaN;
        double sum = 0; int count = 0;
        for (int i = Math.max(1, n - p); i < n; i++) { sum += dx[i]; count++; }
        return count > 0 ? sum / count : Double.NaN;
    }

    private static double volumeRatio(double[] v, int n) {
        if (v == null || n < 24) return 1.0;
        double recent = 0, base = 0;
        for (int i = n - 3; i < n; i++) recent += Math.max(0, v[i]);
        for (int i = n - 23; i < n - 3; i++) base += Math.max(0, v[i]);
        recent /= 3.0; base /= 20.0;
        return base > 0 ? recent / base : 1.0;
    }

    private static double takerRatio(double[] v, double[] tb, int n) {
        if (v == null || tb == null || n < 3) return 0.5;
        double vv = 0, bb = 0;
        for (int i = n - 3; i < n; i++) { vv += Math.max(0, v[i]); bb += Math.max(0, tb[i]); }
        return vv > 0 ? bb / vv : 0.5;
    }

    private static double vwap(double[] h, double[] l, double[] c, double[] v) {
        double pv = 0, vol = 0;
        for (int i = Math.max(0, c.length - 120); i < c.length; i++) {
            if (v[i] <= 0) continue;
            double tp = (h[i] + l[i] + c[i]) / 3.0;
            pv += tp * v[i]; vol += v[i];
        }
        return vol > 0 ? pv / vol : Double.NaN;
    }

    private static double mean(double[] a, int from, int to) {
        if (to <= from) return Double.NaN;
        double s = 0; for (int i = from; i < to; i++) s += a[i];
        return s / (to - from);
    }
    private static double std(double[] a, int from, int to, double m) {
        if (to <= from || !finite(m)) return 0;
        double s = 0; for (int i = from; i < to; i++) { double d = a[i] - m; s += d * d; }
        return Math.sqrt(s / Math.max(1, to - from));
    }
    private static double max(double[] a, int from, int to) {
        double m = -Double.MAX_VALUE; for (int i = from; i < to; i++) m = Math.max(m, a[i]); return m;
    }
    private static double min(double[] a, int from, int to) {
        double m = Double.MAX_VALUE; for (int i = from; i < to; i++) m = Math.min(m, a[i]); return m;
    }
}

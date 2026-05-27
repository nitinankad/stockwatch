export function getPredictionSeries(history: number[], steps = 4): number[] {
  if (history.length === 0) return [];

  const last = history[history.length - 1];
  const recent = history.slice(-6);
  const deltas = recent.slice(1).map((value, index) => value - recent[index]);
  const avgDelta = deltas.length
    ? deltas.reduce((sum, delta) => sum + delta, 0) / deltas.length
    : 0;

  return Array.from({ length: steps }, (_, index) => {
    const step = index + 1;
    const dampening = Math.max(0.65, 1 - index * 0.08);
    return last + avgDelta * step * dampening;
  });
}

export function getPredictedPrice(history: number[]): number {
  const prediction = getPredictionSeries(history);
  return prediction[prediction.length - 1] ?? history[history.length - 1] ?? 0;
}

export type HorizonPrediction = {
  horizon: '1h' | '4h' | '1d' | '1w';
  label: string;
  prob: number;
  direction: 'bullish' | 'bearish';
};

function seededRand(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(31, h) + seed.charCodeAt(i) | 0;
  }
  return (h >>> 0) / 4294967296;
}

export function getHorizonPredictions(ticker: string, sentimentScore: number): HorizonPrediction[] {
  const horizons: Array<{ id: '1h' | '4h' | '1d' | '1w'; label: string; noise: number }> = [
    { id: '1h', label: '1 Hour',  noise: 0.14 },
    { id: '4h', label: '4 Hours', noise: 0.10 },
    { id: '1d', label: '1 Day',   noise: 0.06 },
    { id: '1w', label: '1 Week',  noise: 0.04 },
  ];

  const base = sentimentScore / 100;
  return horizons.map(({ id, label, noise }) => {
    const r = seededRand(ticker + id);
    const jitter = (r - 0.5) * noise;
    const prob = Math.max(0.28, Math.min(0.86, base + jitter));
    return { horizon: id, label, prob, direction: prob >= 0.5 ? 'bullish' : 'bearish' } as HorizonPrediction;
  });
}

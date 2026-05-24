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

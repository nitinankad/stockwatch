import { useState, useEffect, useRef } from 'react';
import { STOCK_DATABASE } from '../data/stocks';
import { getPredictedPrice, getPredictionSeries } from '../utils/prediction';
import type { WatchlistItem } from '../types';

type StockPageProps = {
  ticker: string;
  watchlists: WatchlistItem[];
  onBack: () => void;
  onToggleWatchlist: (watchlistId: number, ticker: string) => void;
};

// ── Icons ─────────────────────────────────────────────────────

function ChevronLeft() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M9 2L3 7l6 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
      <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
      <path d="M2 7l4 4 6-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ── Chart ─────────────────────────────────────────────────────

function StockChart({ ticker, history, priceUp }: { ticker: string; history: number[]; priceUp: boolean }) {
  const w = 800, h = 140;
  const prediction = getPredictionSeries(history);
  const chartValues = [...history, ...prediction];
  const min = Math.min(...chartValues);
  const max = Math.max(...chartValues);
  const range = max - min || 1;
  const padT = 12, padB = 8;
  const innerH = h - padT - padB;
  const gradId = `sp-grad-${ticker.replace(/[^a-zA-Z0-9]/g, '_')}`;
  const color = priceUp ? '#16a34a' : '#dc2626';
  const predictionColor = '#2563eb';
  const historyW = w * 0.78;

  const pts = history.map((v, i) => [
    (i / (history.length - 1)) * historyW,
    padT + (1 - (v - min) / range) * innerH,
  ] as [number, number]);
  const predictionPts = prediction.map((v, i) => [
    historyW + ((i + 1) / prediction.length) * (w - historyW),
    padT + (1 - (v - min) / range) * innerH,
  ] as [number, number]);

  const linePath = `M ${pts.map(([x, y]) => `${x},${y}`).join(' L ')}`;
  const areaPath = `${linePath} L ${historyW},${h} L 0,${h} Z`;
  const lastPt = pts[pts.length - 1];
  const predictionPath = `M ${[lastPt, ...predictionPts].map(([x, y]) => `${x},${y}`).join(' L ')}`;
  const predictionEnd = predictionPts[predictionPts.length - 1];

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block', height: '140px' }}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path
        d={predictionPath}
        fill="none"
        stroke={predictionColor}
        strokeWidth="2.5"
        strokeDasharray="7 7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={lastPt[0]} cy={lastPt[1]} r="4" fill={color} />
      <circle cx={predictionEnd[0]} cy={predictionEnd[1]} r="4" fill="#fff" stroke={predictionColor} strokeWidth="2.5" />
    </svg>
  );
}

// ── 52W Range Bar ─────────────────────────────────────────────

function RangeBar({ price, low, high }: { price: number; low: number; high: number }) {
  const pct = Math.min(100, Math.max(0, ((price - low) / (high - low)) * 100));
  return (
    <div className="sp-range-section">
      <span className="sp-range-heading">52-Week Range</span>
      <div className="sp-range-bar-wrap">
        <span className="sp-range-bound">${low.toFixed(2)}</span>
        <div className="sp-range-track">
          <div className="sp-range-fill" style={{ width: `${pct}%` }} />
          <div className="sp-range-cursor" style={{ left: `${pct}%` }} />
        </div>
        <span className="sp-range-bound right">${high.toFixed(2)}</span>
      </div>
      <span className="sp-range-label">Current: ${price.toFixed(2)}</span>
    </div>
  );
}

// ── Stats Grid ────────────────────────────────────────────────

function StatItem({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="sp-stat-row">
      <span className="sp-stat-label">{label}</span>
      {value ? (
        <span className="sp-stat-value">{value}</span>
      ) : (
        <span className="sp-stat-null">N/A</span>
      )}
    </div>
  );
}

// ── Add to Watchlist dropdown ─────────────────────────────────

function AddToWatchlist({
  ticker,
  watchlists,
  onToggle,
}: {
  ticker: string;
  watchlists: WatchlistItem[];
  onToggle: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, []);

  return (
    <div className="sp-add-wl-wrap" ref={ref}>
      <button className="sp-add-wl-btn" onClick={() => setOpen(v => !v)}>
        <PlusIcon />
        Add to Watchlist
      </button>
      {open && (
        <div className="sp-wl-dropdown">
          <span className="sp-wl-dropdown-label">Your Watchlists</span>
          {watchlists.map(wl => {
            const inList = wl.stocks.includes(ticker);
            return (
              <button
                key={wl.id}
                className="sp-wl-item"
                onClick={() => { onToggle(wl.id); }}
              >
                <span className="sp-wl-item-name">{wl.name}</span>
                {inList && (
                  <span className="sp-wl-item-check">
                    <CheckIcon />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────

export function StockPage({ ticker, watchlists, onBack, onToggleWatchlist }: StockPageProps) {
  const info = STOCK_DATABASE[ticker];

  if (!info) {
    return (
      <div className="sp-page">
        <div className="sp-inner">
          <button className="sp-back-btn" onClick={onBack}>
            <ChevronLeft /> Back
          </button>
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-s)' }}>
            <p style={{ fontSize: '18px', fontWeight: 700 }}>Unknown ticker: {ticker}</p>
            <p style={{ fontSize: '13.5px', marginTop: '8px' }}>No data found in our database.</p>
          </div>
        </div>
      </div>
    );
  }

  const sign = info.priceUp ? '+' : '';
  const { stats } = info;
  const predictedPrice = getPredictedPrice(info.history);
  const predictionDiff = predictedPrice - info.price;
  const predictionPct = info.price === 0 ? 0 : (predictionDiff / info.price) * 100;

  return (
    <div className="sp-page">
      <div className="sp-inner">

        {/* Top bar */}
        <div className="sp-topbar">
          <button className="sp-back-btn" onClick={onBack}>
            <ChevronLeft /> Back
          </button>
          <AddToWatchlist
            ticker={ticker}
            watchlists={watchlists}
            onToggle={id => onToggleWatchlist(id, ticker)}
          />
        </div>

        {/* Hero */}
        <div className="sp-hero">
          <div className="sp-ticker-row">
            <span className="sp-ticker">{info.ticker}</span>
            <span className="sp-company">{info.company}</span>
          </div>
          <div className="sp-price-row">
            <span className="sp-price">${info.price.toFixed(2)}</span>
            <div className="sp-change-group">
              <span className={`sp-change ${info.priceUp ? 'up' : 'dn'}`}>
                {sign}{info.change.toFixed(2)}
              </span>
              <span className={`sp-change-pct ${info.priceUp ? 'up' : 'dn'}`}>
                {sign}{info.changePct.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="sp-chart-card">
          <div className="sp-chart-summary">
            <div className="sp-chart-legend">
              <span className="sp-chart-legend-item">
                <span className={`sp-chart-legend-line ${info.priceUp ? 'up' : 'dn'}`} />
                Actual
              </span>
              <span className="sp-chart-legend-item">
                <span className="sp-chart-legend-line prediction" />
                Projection
              </span>
            </div>
            <div className="sp-prediction">
              <span className="sp-prediction-label">Predicted price</span>
              <span className="sp-prediction-value">${predictedPrice.toFixed(2)}</span>
              <span className={`sp-prediction-delta ${predictionDiff >= 0 ? 'up' : 'dn'}`}>
                {predictionDiff >= 0 ? '+' : ''}{predictionPct.toFixed(1)}%
              </span>
            </div>
          </div>
          <StockChart ticker={info.ticker} history={info.history} priceUp={info.priceUp} />
          <div style={{ marginTop: '16px' }}>
            <RangeBar price={info.price} low={stats.low52w} high={stats.high52w} />
          </div>
        </div>

        {/* Stats */}
        <div className="sp-stats-card">
          <span className="sp-stats-heading">Key Statistics</span>
          <div className="sp-stats-grid">
            <StatItem label="Market Cap" value={stats.marketCap} />
            <StatItem label="P/E Ratio" value={stats.peRatio} />
            <StatItem label="Volume" value={stats.volume} />
            <StatItem label="Avg Volume" value={stats.avgVolume} />
            <StatItem label="EPS (TTM)" value={stats.eps} />
            <StatItem label="Revenue TTM" value={stats.revenueTTM} />
            <StatItem label="Dividend Yield" value={stats.divYield} />
            <StatItem label="Beta" value={stats.beta} />
          </div>
        </div>

        {/* Analysis */}
        <div className="sp-analysis-card">
          <div className="sc-sentiment">
            <span className={`sc-sentiment-badge sc-sentiment-${info.sentiment}`}>
              <span className="sc-sentiment-dot" />
              {info.sentiment.toUpperCase()}&nbsp;&nbsp;{info.sentimentScore}%
            </span>
            <p className="sc-sentiment-text">{info.sentimentSummary}</p>
          </div>

          <div className="sc-news">
            <span className="sc-news-heading">Latest News</span>
            {info.news.map((item, i) => (
              <div key={i} className="sc-news-item">
                <span className={`sc-news-dot sc-news-dot-${item.sentiment}`} />
                <div className="sc-news-content">
                  <span className="sc-news-headline">{item.headline}</span>
                  <span className="sc-news-meta">{item.source} · {item.timeAgo} ago</span>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

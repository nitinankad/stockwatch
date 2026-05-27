import { useState, useEffect, useRef } from 'react';
import { STOCK_DATABASE } from '../data/stocks';
import type { StockInfo, StockStats } from '../data/stocks';
import { getHorizonPredictions } from '../utils/prediction';
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

// ── Chart (historical only) ────────────────────────────────────

function StockChart({ ticker, history, priceUp }: { ticker: string; history: number[]; priceUp: boolean }) {
  const w = 800, h = 140;
  const min = Math.min(...history);
  const max = Math.max(...history);
  const range = max - min || 1;
  const padT = 12, padB = 8;
  const innerH = h - padT - padB;
  const gradId = `sp-grad-${ticker.replace(/[^a-zA-Z0-9]/g, '_')}`;
  const color = priceUp ? '#16a34a' : '#dc2626';

  const pts = history.map((v, i) => [
    (i / (history.length - 1)) * w,
    padT + (1 - (v - min) / range) * innerH,
  ] as [number, number]);

  const linePath = `M ${pts.map(([x, y]) => `${x},${y}`).join(' L ')}`;
  const areaPath = `${linePath} L ${w},${h} L 0,${h} Z`;
  const lastPt = pts[pts.length - 1];

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
      <circle cx={lastPt[0]} cy={lastPt[1]} r="4" fill={color} />
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

// ── Predictions Card ──────────────────────────────────────────

const HORIZON_SIGNALS: Record<'bullish' | 'bearish', Record<string, string>> = {
  bullish: {
    '1h': 'Near-term momentum and elevated volume support continued upside pressure.',
    '4h': 'Momentum indicators are positive. Short-term trend remains intact.',
    '1d': 'Daily technical setup is constructive. Sentiment and price action align.',
    '1w': 'Weekly outlook is positive. Fundamental backdrop supports the trend.',
  },
  bearish: {
    '1h': 'Intraday signals show distribution. Near-term caution is warranted.',
    '4h': 'Momentum is rolling over. Risk/reward is unfavorable in the near term.',
    '1d': 'Daily trend favors downside. Bearish sentiment confirms the pressure.',
    '1w': 'Weak weekly setup. Fundamental backdrop adds to the downside risk.',
  },
};

function PredictionsCard({ info }: { info: StockInfo }) {
  const predictions = getHorizonPredictions(info.ticker, info.sentimentScore);
  const [activeIdx, setActiveIdx] = useState(0);
  const active = predictions[activeIdx];
  const isBull = active.direction === 'bullish';
  const confPct = Math.round(active.prob * 100);

  return (
    <div className="sp-pred-card">
      <div className="sp-pred-header">
        <span className="sp-pred-title">AI Predictions</span>
        <div className="sp-pred-tabs">
          {predictions.map((p, i) => (
            <button
              key={p.horizon}
              className={`sp-pred-tab${i === activeIdx ? ' active' : ''}`}
              onClick={() => setActiveIdx(i)}
            >
              {p.horizon}
            </button>
          ))}
        </div>
      </div>

      <div className="sp-pred-body">
        <div className={`sp-pred-direction ${isBull ? 'bull' : 'bear'}`}>
          <span className="sp-pred-arrow">{isBull ? '↑' : '↓'}</span>
          <div className="sp-pred-dir-text">
            <span className="sp-pred-dir-label">{isBull ? 'BULLISH' : 'BEARISH'}</span>
            <span className="sp-pred-dir-sub">{active.label} outlook</span>
          </div>
          <span className="sp-pred-conf-num">{confPct}%</span>
        </div>

        <div className="sp-pred-bar-wrap">
          <div className="sp-pred-bar-track">
            <div
              className={`sp-pred-bar-fill ${isBull ? 'bull' : 'bear'}`}
              style={{ width: `${active.prob * 100}%` }}
            />
            <div className="sp-pred-bar-mid" />
          </div>
          <div className="sp-pred-bar-labels">
            <span>Bearish</span>
            <span>Baseline 50%</span>
            <span>Bullish</span>
          </div>
        </div>

        <p className="sp-pred-signal">
          {HORIZON_SIGNALS[active.direction][active.horizon]}
        </p>
      </div>
    </div>
  );
}

// ── Stats Card (collapsible) ──────────────────────────────────

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

function StatsCard({ stats }: { stats: StockStats }) {
  const [expanded, setExpanded] = useState(false);

  const primary = [
    { label: 'Market Cap',    value: stats.marketCap },
    { label: 'P/E Ratio',     value: stats.peRatio },
    { label: 'Volume',        value: stats.volume },
    { label: 'EPS (TTM)',     value: stats.eps },
  ];
  const secondary = [
    { label: 'Avg Volume',     value: stats.avgVolume },
    { label: 'Revenue TTM',    value: stats.revenueTTM },
    { label: 'Dividend Yield', value: stats.divYield },
    { label: 'Beta',           value: stats.beta },
  ];
  const displayed = expanded ? [...primary, ...secondary] : primary;

  return (
    <div className="sp-stats-card">
      <div className="sp-stats-hrow">
        <span className="sp-stats-heading">Key Statistics</span>
        <button className="sp-stats-toggle" onClick={() => setExpanded(v => !v)}>
          {expanded ? 'Collapse' : 'View all'}
        </button>
      </div>
      <div className="sp-stats-grid">
        {displayed.map(s => (
          <StatItem key={s.label} label={s.label} value={s.value} />
        ))}
      </div>
    </div>
  );
}

// ── Analysis Card (news collapsible) ─────────────────────────

function AnalysisCard({ info }: { info: StockInfo }) {
  const [newsOpen, setNewsOpen] = useState(false);
  const shown = newsOpen ? info.news : info.news.slice(0, 1);
  const extra = info.news.length - 1;

  return (
    <div className="sp-analysis-card">
      <div className="sc-sentiment">
        <span className={`sc-sentiment-badge sc-sentiment-${info.sentiment}`}>
          <span className="sc-sentiment-dot" />
          {info.sentiment.toUpperCase()}&nbsp;&nbsp;{info.sentimentScore}%
        </span>
        <p className="sc-sentiment-text">{info.sentimentSummary}</p>
      </div>

      <div className="sc-news">
        <div className="sc-news-hrow">
          <span className="sc-news-heading">Latest News</span>
          {extra > 0 && (
            <button className="sc-news-toggle" onClick={() => setNewsOpen(v => !v)}>
              {newsOpen ? 'Collapse' : `+${extra} more`}
            </button>
          )}
        </div>
        {shown.map((item, i) => (
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

        {/* AI Predictions */}
        <PredictionsCard info={info} />

        {/* Chart */}
        <div className="sp-chart-card">
          <StockChart ticker={info.ticker} history={info.history} priceUp={info.priceUp} />
          <div style={{ marginTop: '16px' }}>
            <RangeBar price={info.price} low={info.stats.low52w} high={info.stats.high52w} />
          </div>
        </div>

        {/* Stats */}
        <StatsCard stats={info.stats} />

        {/* Analysis */}
        <AnalysisCard info={info} />

      </div>
    </div>
  );
}

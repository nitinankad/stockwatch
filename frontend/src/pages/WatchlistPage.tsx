import { useState, useRef, useEffect } from 'react';
import { STOCK_DATABASE, SEARCH_LIST, type StockInfo } from '../data/stocks';
import { getPredictedPrice, getPredictionSeries } from '../utils/prediction';
import type { WatchlistItem } from '../types';

type WatchlistPageProps = {
  watchlist: WatchlistItem;
  onBack: () => void;
  onUpdateStocks: (stocks: string[]) => void;
  onDeleteWatchlist: () => void;
  navigate: (path: string) => void;
};

// ── Icons ────────────────────────────────────────────────────

function SearchIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
      <rect x="2.5" y="6.5" width="9" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M4.5 6.5V4.5a2.5 2.5 0 015 0v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.4"/>
      <ellipse cx="7" cy="7" rx="2.2" ry="5.5" stroke="currentColor" strokeWidth="1.4"/>
      <path d="M1.5 7h11" stroke="currentColor" strokeWidth="1.4"/>
    </svg>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="14" height="14" viewBox="0 0 14 14" fill="none"
      style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .2s ease' }}
    >
      <path d="M2 5l5 4.5L12 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ── Stock chart ───────────────────────────────────────────────

function StockChart({ ticker, history, priceUp }: { ticker: string; history: number[]; priceUp: boolean }) {
  const w = 600, h = 80;
  const prediction = getPredictionSeries(history);
  const chartValues = [...history, ...prediction];
  const min = Math.min(...chartValues);
  const max = Math.max(...chartValues);
  const range = max - min || 1;
  const padT = 8, padB = 6;
  const innerH = h - padT - padB;
  const gradId = `sc-grad-${ticker.replace(/[^a-zA-Z0-9]/g, '_')}`;
  const color = priceUp ? '#16a34a' : '#dc2626';
  const predictionColor = '#2563eb';
  const historyW = w * 0.76;

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
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block', height: '80px' }}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path
        d={predictionPath}
        fill="none"
        stroke={predictionColor}
        strokeWidth="2"
        strokeDasharray="6 6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={lastPt[0]} cy={lastPt[1]} r="3.5" fill={color} />
      <circle cx={predictionEnd[0]} cy={predictionEnd[1]} r="3.5" fill="#fff" stroke={predictionColor} strokeWidth="2" />
    </svg>
  );
}

// ── Stock card ────────────────────────────────────────────────

function StockCard({
  info,
  isExpanded,
  onToggle,
  onRequestRemove,
  navigate,
}: {
  info: StockInfo;
  isExpanded: boolean;
  onToggle: () => void;
  onRequestRemove: () => void;
  navigate: (path: string) => void;
}) {
  const sign = info.priceUp ? '+' : '';
  const predictedPrice = getPredictedPrice(info.history);
  const predictionDiff = predictedPrice - info.price;
  const predictionPct = info.price === 0 ? 0 : (predictionDiff / info.price) * 100;

  return (
    <div className="sc-card">
      {/* Header row — always visible, click to expand/collapse */}
      <div
        className="sc-header"
        onClick={onToggle}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && onToggle()}
      >
        <div className="sc-ticker-group">
          <button
            className="sc-ticker sc-ticker-link"
            onClick={e => { e.stopPropagation(); navigate(`/stocks/${info.ticker}`); }}
            title={`View ${info.ticker} detail`}
          >
            {info.ticker}
          </button>
          <span className="sc-company">{info.company}</span>
        </div>
        <div className="sc-price-group">
          <span className="sc-price">${info.price.toFixed(2)}</span>
          <div className="sc-change-block">
            <span className={`sc-change ${info.priceUp ? 'up' : 'dn'}`}>
              {sign}{info.change.toFixed(2)}
            </span>
            <span className={`sc-change-pct ${info.priceUp ? 'up' : 'dn'}`}>
              {sign}{info.changePct.toFixed(2)}%
            </span>
          </div>
        </div>
        <span className="sc-chevron">
          <ChevronIcon open={isExpanded} />
        </span>
        <button
          className="sc-remove-btn"
          onClick={e => { e.stopPropagation(); onRequestRemove(); }}
          title="Remove from watchlist"
        >
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
            <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="sc-expanded-content">
          <div className="sc-chart-summary">
            <div className="sc-chart-legend">
              <span className="sc-chart-legend-item">
                <span className={`sc-chart-legend-line ${info.priceUp ? 'up' : 'dn'}`} />
                Actual
              </span>
              <span className="sc-chart-legend-item">
                <span className="sc-chart-legend-line prediction" />
                Projection
              </span>
            </div>
            <div className="sc-prediction">
              <span className="sc-prediction-label">Predicted</span>
              <span className="sc-prediction-value">${predictedPrice.toFixed(2)}</span>
              <span className={`sc-prediction-delta ${predictionDiff >= 0 ? 'up' : 'dn'}`}>
                {predictionDiff >= 0 ? '+' : ''}{predictionPct.toFixed(1)}%
              </span>
            </div>
          </div>
          <StockChart ticker={info.ticker} history={info.history} priceUp={info.priceUp} />

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
      )}
    </div>
  );
}

// Delete confirmation modal

function DeleteStockModal({
  ticker,
  watchlistName,
  onCancel,
  onConfirm,
}: {
  ticker: string;
  watchlistName: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="wl-modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <div
        className="wl-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="wl-delete-title"
        onMouseDown={e => e.stopPropagation()}
      >
        <div className="wl-modal-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M3 6h18" />
            <path d="M8 6V4h8v2" />
            <path d="M19 6l-1 14H6L5 6" />
            <path d="M10 11v5M14 11v5" />
          </svg>
        </div>
        <div className="wl-modal-copy">
          <h2 id="wl-delete-title" className="wl-modal-title">Remove {ticker}?</h2>
          <p className="wl-modal-text">
            Are you sure you want to delete this stock from the {watchlistName} watchlist?
          </p>
        </div>
        <div className="wl-modal-actions">
          <button className="wl-modal-cancel" onClick={onCancel}>
            Cancel
          </button>
          <button className="wl-modal-confirm" onClick={onConfirm}>
            Delete stock
          </button>
        </div>
      </div>
    </div>
  );
}

function DeleteWatchlistModal({
  watchlistName,
  stockCount,
  onCancel,
  onConfirm,
}: {
  watchlistName: string;
  stockCount: number;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="wl-modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <div
        className="wl-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="wl-delete-watchlist-title"
        onMouseDown={e => e.stopPropagation()}
      >
        <div className="wl-modal-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M3 6h18" />
            <path d="M8 6V4h8v2" />
            <path d="M19 6l-1 14H6L5 6" />
            <path d="M10 11v5M14 11v5" />
          </svg>
        </div>
        <div className="wl-modal-copy">
          <h2 id="wl-delete-watchlist-title" className="wl-modal-title">Delete {watchlistName}?</h2>
          <p className="wl-modal-text">
            This will delete the watchlist and remove {stockCount} {stockCount === 1 ? 'stock' : 'stocks'} from it. This action cannot be undone.
          </p>
        </div>
        <div className="wl-modal-actions">
          <button className="wl-modal-cancel" onClick={onCancel}>
            Cancel
          </button>
          <button className="wl-modal-confirm" onClick={onConfirm}>
            Delete watchlist
          </button>
        </div>
      </div>
    </div>
  );
}

// Unknown ticker card

function UnknownCard({ ticker, onRemove }: { ticker: string; onRemove: () => void }) {
  return (
    <div className="sc-card sc-card-unknown">
      <div className="sc-header" style={{ cursor: 'default' }}>
        <div className="sc-ticker-group">
          <span className="sc-ticker">{ticker}</span>
          <span className="sc-company">No data available</span>
        </div>
        <button className="sc-remove-btn" onClick={onRemove} title="Remove">
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
            <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────

export function WatchlistPage({ watchlist, onBack, onUpdateStocks, onDeleteWatchlist, navigate }: WatchlistPageProps) {
  const [stocks, setStocks] = useState<string[]>(watchlist.stocks);
  const [isPublic, setIsPublic] = useState(watchlist.isPublic);
  const [query, setQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const [expandedTickers, setExpandedTickers] = useState<Set<string>>(new Set());
  const [pendingDeleteTicker, setPendingDeleteTicker] = useState<string | null>(null);
  const [deleteWatchlistOpen, setDeleteWatchlistOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  const suggestions =
    searchFocused && query.trim().length > 0
      ? SEARCH_LIST.filter(
          s =>
            !stocks.includes(s.ticker) &&
            (s.ticker.toLowerCase().startsWith(query.toLowerCase()) ||
              s.company.toLowerCase().includes(query.toLowerCase())),
        ).slice(0, 6)
      : [];

  const allExpanded = stocks.length > 0 && stocks.every(t => expandedTickers.has(t));

  function toggleExpand(ticker: string) {
    setExpandedTickers(prev => {
      const next = new Set(prev);
      if (next.has(ticker)) next.delete(ticker);
      else next.add(ticker);
      return next;
    });
  }

  function toggleAll() {
    if (allExpanded) setExpandedTickers(new Set());
    else setExpandedTickers(new Set(stocks));
  }

  function addStock(ticker: string) {
    const next = [...stocks, ticker];
    setStocks(next);
    onUpdateStocks(next);
    setQuery('');
    setSearchFocused(false);
    setExpandedTickers(prev => new Set([...prev, ticker]));
  }

  function removeStock(ticker: string) {
    const next = stocks.filter(s => s !== ticker);
    setStocks(next);
    onUpdateStocks(next);
    setExpandedTickers(prev => { const n = new Set(prev); n.delete(ticker); return n; });
    setPendingDeleteTicker(null);
  }

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchFocused(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== 'Escape') return;
      setPendingDeleteTicker(null);
      setDeleteWatchlistOpen(false);
    }

    if (pendingDeleteTicker || deleteWatchlistOpen) document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [pendingDeleteTicker, deleteWatchlistOpen]);

  return (
    <div className="wp-page">
      <div className="wp-inner">

        {/* Back */}
        <button className="wp-back-btn" onClick={onBack}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M9 2L3 7l6 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          My Watchlists
        </button>

        {/* Header */}
        <div className="wp-header">
          <h1 className="wp-name">{watchlist.name}</h1>
          <div className="wp-header-right">
            <button
              className="wp-delete-btn"
              onClick={() => setDeleteWatchlistOpen(true)}
              title="Delete watchlist"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <path d="M3 6h18" />
                <path d="M8 6V4h8v2" />
                <path d="M19 6l-1 14H6L5 6" />
                <path d="M10 11v5M14 11v5" />
              </svg>
              Delete
            </button>
            <button
              className={`wp-privacy-btn ${isPublic ? 'wp-privacy-public' : 'wp-privacy-private'}`}
              onClick={() => setIsPublic(v => !v)}
              title={isPublic ? 'Click to make private' : 'Click to share publicly'}
            >
              {isPublic ? <GlobeIcon /> : <LockIcon />}
              {isPublic ? 'Public' : 'Private'}
            </button>
            {!isPublic && (
              <button className="wp-share-btn" onClick={() => setIsPublic(true)}>
                Share
              </button>
            )}
          </div>
        </div>

        {/* Add stock search */}
        <div className="wp-add-bar" ref={searchRef}>
          <div className="wp-add-input-wrap">
            <span className="wp-add-search-icon"><SearchIcon /></span>
            <input
              className="wp-add-input"
              placeholder="Search ticker or company to add a stock…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
            />
            {query && (
              <button className="wp-add-clear" onClick={() => { setQuery(''); setSearchFocused(false); }}>
                ×
              </button>
            )}
          </div>
          {suggestions.length > 0 && (
            <div className="wp-suggestions">
              {suggestions.map(s => (
                <button key={s.ticker} className="wp-suggestion" onMouseDown={() => addStock(s.ticker)}>
                  <span className="wp-sug-ticker">{s.ticker}</span>
                  <span className="wp-sug-company">{s.company}</span>
                  <span className="wp-sug-add">+ Add</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* List controls */}
        {stocks.length > 0 && (
          <div className="wp-list-bar">
            <span className="wp-count">
              {stocks.length} {stocks.length === 1 ? 'stock' : 'stocks'}
            </span>
            <button className="wp-expand-btn" onClick={toggleAll}>
              {allExpanded ? 'Collapse all' : 'Expand all'}
            </button>
          </div>
        )}

        {/* Content */}
        {stocks.length === 0 ? (
          <div className="wp-empty">
            <div className="wp-empty-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                <path d="M3 3h18M3 8h18M3 13h10"/>
                <circle cx="17" cy="17" r="4"/>
                <path d="M19.5 19.5L22 22"/>
              </svg>
            </div>
            <p className="wp-empty-text">This watchlist is empty</p>
            <p className="wp-empty-sub">Search above to add stocks you want to track</p>
          </div>
        ) : (
          <div className="wp-stock-list">
            {stocks.map(ticker => {
              const info = STOCK_DATABASE[ticker];
              return info ? (
                <StockCard
                  key={ticker}
                  info={info}
                  isExpanded={expandedTickers.has(ticker)}
                  onToggle={() => toggleExpand(ticker)}
                  onRequestRemove={() => setPendingDeleteTicker(ticker)}
                  navigate={navigate}
                />
              ) : (
                <UnknownCard key={ticker} ticker={ticker} onRemove={() => setPendingDeleteTicker(ticker)} />
              );
            })}
          </div>
        )}

        {pendingDeleteTicker && (
          <DeleteStockModal
            ticker={pendingDeleteTicker}
            watchlistName={watchlist.name}
            onCancel={() => setPendingDeleteTicker(null)}
            onConfirm={() => removeStock(pendingDeleteTicker)}
          />
        )}

        {deleteWatchlistOpen && (
          <DeleteWatchlistModal
            watchlistName={watchlist.name}
            stockCount={stocks.length}
            onCancel={() => setDeleteWatchlistOpen(false)}
            onConfirm={onDeleteWatchlist}
          />
        )}

      </div>
    </div>
  );
}

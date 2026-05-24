import { useState, useRef, useEffect } from 'react';
import { STOCK_DATABASE, SEARCH_LIST, type StockInfo } from '../data/stocks';
import type { WatchlistItem } from '../types';

type WatchlistPageProps = {
  watchlist: WatchlistItem;
  onBack: () => void;
  onUpdateStocks: (stocks: string[]) => void;
};

function StockChart({ ticker, history, priceUp }: { ticker: string; history: number[]; priceUp: boolean }) {
  const w = 600, h = 80;
  const min = Math.min(...history);
  const max = Math.max(...history);
  const range = max - min || 1;
  const padT = 8, padB = 6;
  const innerH = h - padT - padB;
  const gradId = `sc-grad-${ticker.replace(/[^a-zA-Z0-9]/g, '_')}`;
  const color = priceUp ? '#16a34a' : '#dc2626';

  const pts = history.map((v, i) => [
    (i / (history.length - 1)) * w,
    padT + (1 - (v - min) / range) * innerH,
  ] as [number, number]);

  const linePath = `M ${pts.map(([x, y]) => `${x},${y}`).join(' L ')}`;
  const areaPath = `${linePath} L ${w},${h} L 0,${h} Z`;
  const lastPt = pts[pts.length - 1];

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      style={{ display: 'block', height: '80px', borderRadius: '4px' }}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lastPt[0]} cy={lastPt[1]} r="3.5" fill={color} />
    </svg>
  );
}

function StockCard({ info, onRemove }: { info: StockInfo; onRemove: () => void }) {
  const sign = info.priceUp ? '+' : '';

  return (
    <div className="sc-card">
      <div className="sc-header">
        <div className="sc-ticker-group">
          <span className="sc-ticker">{info.ticker}</span>
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
        <button className="sc-remove-btn" onClick={onRemove} title="Remove from watchlist">
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
            <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      <StockChart ticker={info.ticker} history={info.history} priceUp={info.priceUp} />

      <div className="sc-sentiment">
        <span className={`sc-sentiment-badge sc-sentiment-${info.sentiment}`}>
          <span className="sc-sentiment-dot" />
          {info.sentiment.toUpperCase()} &nbsp;{info.sentimentScore}%
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
  );
}

function SearchIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <circle cx="11" cy="11" r="8"/>
      <path d="m21 21-4.35-4.35"/>
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

export function WatchlistPage({ watchlist, onBack, onUpdateStocks }: WatchlistPageProps) {
  const [stocks, setStocks] = useState<string[]>(watchlist.stocks);
  const [isPublic, setIsPublic] = useState(watchlist.isPublic);
  const [query, setQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
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

  function addStock(ticker: string) {
    const next = [...stocks, ticker];
    setStocks(next);
    onUpdateStocks(next);
    setQuery('');
    setSearchFocused(false);
  }

  function removeStock(ticker: string) {
    const next = stocks.filter(s => s !== ticker);
    setStocks(next);
    onUpdateStocks(next);
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

        {/* Stock count */}
        <div className="wp-count">
          {stocks.length} {stocks.length === 1 ? 'stock' : 'stocks'}
        </div>

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
              if (!info) return (
                <div key={ticker} className="sc-card sc-card-unknown">
                  <div className="sc-header">
                    <div className="sc-ticker-group">
                      <span className="sc-ticker">{ticker}</span>
                      <span className="sc-company">No data available</span>
                    </div>
                    <button className="sc-remove-btn" onClick={() => removeStock(ticker)} title="Remove">
                      <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                        <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                      </svg>
                    </button>
                  </div>
                </div>
              );
              return (
                <StockCard key={ticker} info={info} onRemove={() => removeStock(ticker)} />
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
}

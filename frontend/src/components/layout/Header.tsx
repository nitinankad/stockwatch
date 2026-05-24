import { useState, useRef, useEffect } from 'react';
import { STOCK_DATABASE } from '../../data/stocks';
import type { WatchlistItem } from '../../types';

const TICKERS = [
  { sym: 'SPY', change: '+0.42%', up: true  },
  { sym: 'QQQ', change: '+0.81%', up: true  },
  { sym: 'DIA', change: '-0.18%', up: false },
  { sym: 'VIX', change: '-2.41%', up: false },
] as const;

const STOCK_LIST = Object.values(STOCK_DATABASE).map(s => ({
  ticker: s.ticker,
  company: s.company,
  price: s.price,
  changePct: s.changePct,
  priceUp: s.priceUp,
}));

interface HeaderProps {
  onMenuClick: () => void;
  watchlists: WatchlistItem[];
  navigate: (path: string) => void;
}

function ListIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
      <path d="M2 4h10M2 7h7M2 10h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

export function Header({ onMenuClick, watchlists, navigate }: HeaderProps) {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  const q = query.trim().toLowerCase();
  const showDropdown = focused && q.length > 0;

  const stockHits = showDropdown
    ? STOCK_LIST.filter(
        s =>
          s.ticker.toLowerCase().startsWith(q) ||
          s.company.toLowerCase().includes(q),
      ).slice(0, 5)
    : [];

  const watchlistHits = showDropdown
    ? watchlists
        .filter(w => w.name.toLowerCase().includes(q))
        .slice(0, 3)
    : [];

  const hasResults = stockHits.length > 0 || watchlistHits.length > 0;

  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setFocused(false);
      }
    }
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, []);

  function pick(path: string) {
    navigate(path);
    setQuery('');
    setFocused(false);
  }

  return (
    <header className="app-header">
      <button className="menu-btn" onClick={onMenuClick} aria-label="Toggle menu">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <line x1="3" y1="6"  x2="21" y2="6"  />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <div className="search-wrapper" ref={wrapRef}>
        <div className="search-bar">
          <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            className="search-input"
            placeholder="Search tickers or watchlists…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}
            onKeyDown={e => {
              if (e.key === 'Escape') { setFocused(false); setQuery(''); }
              if (e.key === 'Enter' && stockHits.length > 0) pick(`/stocks/${stockHits[0].ticker}`);
            }}
          />
          {query && (
            <button
              className="search-clear"
              onMouseDown={e => { e.preventDefault(); setQuery(''); }}
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>

        {showDropdown && hasResults && (
          <div className="hdr-dropdown">
            {stockHits.length > 0 && (
              <div className="hdr-dropdown-section">
                <span className="hdr-dropdown-label">Stocks</span>
                {stockHits.map(s => (
                  <button
                    key={s.ticker}
                    className="hdr-dropdown-item"
                    onMouseDown={() => pick(`/stocks/${s.ticker}`)}
                  >
                    <span className="hdr-dropdown-sym">{s.ticker}</span>
                    <span className="hdr-dropdown-name">{s.company}</span>
                    <span className="hdr-dropdown-price">${s.price.toFixed(2)}</span>
                    <span className={`hdr-dropdown-change ${s.priceUp ? 'up' : 'dn'}`}>
                      {s.priceUp ? '+' : ''}{s.changePct.toFixed(2)}%
                    </span>
                  </button>
                ))}
              </div>
            )}
            {watchlistHits.length > 0 && (
              <div className="hdr-dropdown-section">
                <span className="hdr-dropdown-label">Watchlists</span>
                {watchlistHits.map(wl => (
                  <button
                    key={wl.id}
                    className="hdr-dropdown-item"
                    onMouseDown={() => pick(`/watchlist/${wl.id}`)}
                  >
                    <span className="hdr-dropdown-wl-icon">
                      <ListIcon />
                    </span>
                    <span className="hdr-dropdown-wl-name">{wl.name}</span>
                    <span className="hdr-dropdown-wl-count">
                      {wl.stocks.length} {wl.stocks.length === 1 ? 'stock' : 'stocks'}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {showDropdown && !hasResults && (
          <div className="hdr-dropdown">
            <div className="hdr-dropdown-section">
              <span className="hdr-dropdown-label" style={{ display: 'block', padding: '14px 16px', color: 'var(--text-m)', fontSize: '13px', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
                No results for "{query}"
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="tickers">
        {TICKERS.map(t => (
          <div key={t.sym} className="ticker">
            <span className="ticker-sym">{t.sym}</span>
            <span className={`ticker-chg ${t.up ? 'up' : 'dn'}`}>{t.change}</span>
          </div>
        ))}
      </div>

      <div className="header-actions">
        <button className="icon-btn" aria-label="Notifications">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <span className="notif-dot" />
        </button>
        <div className="user-avatar" role="button" aria-label="User menu">Y</div>
      </div>
    </header>
  );
}

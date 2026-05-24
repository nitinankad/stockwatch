const TICKERS = [
  { sym: 'SPY', change: '+0.42%', up: true  },
  { sym: 'QQQ', change: '+0.81%', up: true  },
  { sym: 'DIA', change: '-0.18%', up: false },
  { sym: 'VIX', change: '-2.41%', up: false },
] as const;

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="app-header">
      <button className="menu-btn" onClick={onMenuClick} aria-label="Toggle menu">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <line x1="3" y1="6"  x2="21" y2="6"  />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <div className="search-bar">
        <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input className="search-input" placeholder="Search tickers, lists, groups…" />
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

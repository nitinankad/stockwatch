import { useState } from 'react';
import type { WatchlistItem } from '../types';

type HomePageProps = {
  watchlists: WatchlistItem[];
  onOpenWatchlist: (id: number) => void;
};

const DISCOVER = [
  {
    initials: 'SR', author: 'Sofia Reyes', color: '#0ea5e9',
    title: "Dividend compounders I've held for 5+ years",
    description: 'Boring but beautiful. These slow-movers have quietly tripled while everyone chased memes.',
    tickers: ['JNJ', 'KO', 'PG', 'VZ'], followers: '843',
  },
  {
    initials: 'AT', author: 'Alex Tanner', color: '#8b5cf6',
    title: 'Small-cap breakouts on my radar',
    description: 'High risk, high reward setups forming on the weekly chart with volume confirmation.',
    tickers: ['AEHR', 'IONQ', 'BLNK'], followers: '2.1k',
  },
  {
    initials: 'PK', author: 'Priya K.', color: '#10b981',
    title: 'The infrastructure supercycle watchlist',
    description: 'Grid upgrades, data centers, water systems — the dull picks underpinning every hype trend.',
    tickers: ['PWR', 'GTLS', 'ARIS', 'XYL'], followers: '631',
  },
];

function MiniSpark({ data, up }: { data: number[]; up: boolean }) {
  if (data.length < 2) return null;
  const w = 200, h = 40;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 3;
  const innerH = h - pad * 2;
  const pts = data.map((v, i) => [
    (i / (data.length - 1)) * w,
    pad + (1 - (v - min) / range) * innerH,
  ] as [number, number]);
  const linePath = `M ${pts.map(([x, y]) => `${x},${y}`).join(' L ')}`;
  const color = up ? '#16a34a' : '#dc2626';
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="wl-spark">
      <path d={linePath} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" opacity="0.75" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
      <rect x="2.5" y="6.5" width="9" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M4.5 6.5V4.5a2.5 2.5 0 015 0v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.4"/>
      <ellipse cx="7" cy="7" rx="2.2" ry="5.5" stroke="currentColor" strokeWidth="1.4"/>
      <path d="M1.5 7h11" stroke="currentColor" strokeWidth="1.4"/>
    </svg>
  );
}

function PlusIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

function WatchlistCard({ wl, onOpen }: { wl: WatchlistItem; onOpen: () => void }) {
  const [isPublic, setIsPublic] = useState(wl.isPublic);
  const isEmpty = wl.stocks.length === 0;

  return (
    <div className="wl-card" onClick={onOpen}>
      <div className="wl-card-header">
        <h3 className="wl-card-name">{wl.name}</h3>
        <button
          className={`wl-privacy-badge ${isPublic ? 'wl-privacy-public' : 'wl-privacy-private'}`}
          onClick={e => { e.stopPropagation(); setIsPublic(v => !v); }}
          title={isPublic ? 'Click to make private' : 'Click to share publicly'}
        >
          {isPublic ? <GlobeIcon /> : <LockIcon />}
          {isPublic ? 'Public' : 'Private'}
        </button>
      </div>

      {!isEmpty && wl.changeStr !== null && (
        <div className="wl-spark-row">
          <MiniSpark data={wl.sparkData} up={wl.changeUp!} />
          <span className={`wl-change ${wl.changeUp ? 'up' : 'dn'}`}>{wl.changeStr}</span>
        </div>
      )}

      <div className="wl-card-meta">
        <span className="wl-stock-count">
          {wl.stocks.length} {wl.stocks.length === 1 ? 'stock' : 'stocks'}
        </span>
      </div>

      {!isEmpty ? (
        <div className="wl-chips">
          {wl.stocks.slice(0, 5).map(sym => (
            <span key={sym} className="wl-chip">{sym}</span>
          ))}
          {wl.stocks.length > 5 && (
            <span className="wl-chip wl-chip-more">+{wl.stocks.length - 5}</span>
          )}
        </div>
      ) : (
        <div className="wl-empty-state">
          <span className="wl-empty-hint">No stocks yet — add some to get started</span>
        </div>
      )}

      <div className="wl-card-footer">
        <button className="wl-btn-view" onClick={onOpen}>View list</button>
        <button className="wl-btn-add" onClick={e => { e.stopPropagation(); onOpen(); }}>
          <PlusIcon size={11} />
          Add stocks
        </button>
      </div>
    </div>
  );
}

function today() {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
  }).toUpperCase();
}

export function HomePage({ watchlists, onOpenWatchlist }: HomePageProps) {
  return (
    <div className="home-page">
      <div className="home-inner">

        {/* My Watchlists */}
        <section className="home-section">
          <div className="section-hrow">
            <div>
              <span className="home-date">{today()}</span>
              <h2 className="section-title">My Watchlists</h2>
              <p className="section-sub">Track and organize the stocks you care about.</p>
            </div>
            <button className="new-wl-btn">
              <PlusIcon size={13} />
              New Watchlist
            </button>
          </div>

          <div className="wl-grid">
            {watchlists.map(wl => (
              <WatchlistCard key={wl.id} wl={wl} onOpen={() => onOpenWatchlist(wl.id)} />
            ))}
            <button className="wl-create-card">
              <div className="wl-create-icon">
                <PlusIcon size={18} />
              </div>
              <span className="wl-create-label">New watchlist</span>
              <span className="wl-create-hint">Track a new theme or idea</span>
            </button>
          </div>
        </section>

        {/* Discover */}
        <section className="home-section">
          <h3 className="section-heading">Discover public lists</h3>
          <div className="trending-grid">
            {DISCOVER.map(({ initials, author, title, description, tickers, followers, color }) => (
              <div key={author} className="trend-card">
                <div className="trend-top">
                  <div className="trend-avatar" style={{ background: color }}>{initials}</div>
                  <div className="trend-meta">
                    <span className="trend-author">{author}</span>
                    <span className="trend-badge">PUBLIC</span>
                  </div>
                  <span className="trend-followers">{followers} followers</span>
                </div>
                <h4 className="trend-title">{title}</h4>
                <p className="trend-desc">{description}</p>
                <div className="trend-chips">
                  {tickers.map(sym => (
                    <span key={sym} className="trend-chip">{sym}</span>
                  ))}
                </div>
                <div className="trend-actions">
                  <button className="trend-follow-btn">Follow list</button>
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>
    </div>
  );
}

import type { WatchlistItem } from '../../types';
import type { Route } from '../../hooks/useRouter';

interface SideNavProps {
  isOpen: boolean;
  watchlists: WatchlistItem[];
  navigate: (path: string) => void;
  activeRoute: Route;
}

function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M2 6.5L8 2l6 4.5V14a.5.5 0 01-.5.5h-4V10H6.5v4.5h-4A.5.5 0 012 14V6.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
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

export function SideNav({ isOpen, watchlists, navigate, activeRoute }: SideNavProps) {
  const activeWatchlistId = activeRoute.page === 'watchlist' ? activeRoute.id : null;

  return (
    <aside className={`sidebar${isOpen ? ' open' : ''}`}>
      <div className="brand">
        <div className="brand-icon">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <polyline
              points="1,14 5,9 9,11 13,5 17,7"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <div className="brand-text">
          <span className="brand-name">StockWatch</span>
          <span className="brand-beta">Beta</span>
        </div>
      </div>

      <nav className="sidenav-nav">
        <a
          href="/"
          className={`nav-item${activeRoute.page === 'home' ? ' active' : ''}`}
          onClick={e => { e.preventDefault(); navigate('/'); }}
        >
          <HomeIcon />
          <span>Home</span>
        </a>
      </nav>

      <div className="sidenav-section">
        <span className="sidenav-section-label">
          Watchlists
          <a href="#" className="sidenav-section-add" aria-label="New watchlist">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </a>
        </span>
        {watchlists.map(({ id, name, isPublic }) => (
          <a
            key={id}
            href={`/watchlist/${id}`}
            className={`sidenav-list-item${activeWatchlistId === id ? ' sidenav-list-active' : ''}`}
            onClick={e => { e.preventDefault(); navigate(`/watchlist/${id}`); }}
          >
            <span className={`sidenav-privacy-icon ${isPublic ? 'sidenav-privacy-public' : 'sidenav-privacy-private'}`}>
              {isPublic ? <GlobeIcon /> : <LockIcon />}
            </span>
            <span>{name}</span>
          </a>
        ))}
      </div>
    </aside>
  );
}

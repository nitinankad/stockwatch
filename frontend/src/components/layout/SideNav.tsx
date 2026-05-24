interface SideNavProps {
  isOpen: boolean;
}

const NAV_ITEMS = [
  { label: 'Home', icon: HomeIcon, active: true },
  { label: 'My watchlists', icon: ListIcon, active: false },
  { label: 'Groups', icon: GroupIcon, active: false },
];

const YOUR_LISTS = [
  { name: 'Tech Growth', dot: '#b45309' },
  { name: 'Dividend Picks', dot: null },
  { name: 'S&P 500 Watch', dot: null },
  { name: 'Speculative', dot: null },
];

const YOUR_GROUPS = [
  'Quant Traders',
  'Value Investors',
  'Crypto Watch',
];

function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M2 6.5L8 2l6 4.5V14a.5.5 0 01-.5.5h-4V10H6.5v4.5h-4A.5.5 0 012 14V6.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
    </svg>
  );
}

function ListIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M3 4h10M3 8h10M3 12h6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  );
}

function GroupIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="6" cy="5.5" r="2.5" stroke="currentColor" strokeWidth="1.4"/>
      <path d="M1.5 13c0-2.485 2.015-4.5 4.5-4.5S10.5 10.515 10.5 13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
      <path d="M11 4a2 2 0 010 4M14.5 13c0-2-1.343-3.668-3-4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  );
}

export function SideNav({ isOpen }: SideNavProps) {
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
        {NAV_ITEMS.map(({ label, icon: Icon, active }) => (
          <a key={label} href="#" className={`nav-item${active ? ' active' : ''}`}>
            <Icon />
            <span>{label}</span>
          </a>
        ))}

        <a href="#" className="nav-new-watchlist">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
          New watchlist
        </a>
      </nav>

      <div className="sidenav-section">
        <span className="sidenav-section-label">Your Lists</span>
        {YOUR_LISTS.map(({ name, dot }) => (
          <a key={name} href="#" className="sidenav-list-item">
            {dot
              ? <span className="list-dot" style={{ background: dot }} />
              : <span className="list-dot list-dot-empty" />}
            <span>{name}</span>
          </a>
        ))}
      </div>

      <div className="sidenav-section">
        <span className="sidenav-section-label">
          Your Groups
          <a href="#" className="sidenav-section-add">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </a>
        </span>
        {YOUR_GROUPS.map(name => (
          <a key={name} href="#" className="sidenav-list-item sidenav-group-item">
            <span className="group-hash">#</span>
            <span>{name}</span>
          </a>
        ))}
      </div>
    </aside>
  );
}

interface SideNavProps {
  isOpen: boolean;
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
    </aside>
  );
}

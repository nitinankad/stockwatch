import { useState } from 'react';
import { SideNav } from './components/layout/SideNav';
import { Header } from './components/layout/Header';
import { HomePage } from './pages/HomePage';
import { WatchlistPage } from './pages/WatchlistPage';
import type { WatchlistItem } from './types';
import './App.css';

const INITIAL_WATCHLISTS: WatchlistItem[] = [
  {
    id: 1, name: 'Tech Growth', isPublic: false,
    stocks: ['NVDA', 'MSFT', 'AAPL', 'META'],
    changeStr: '+2.4%', changeUp: true,
    sparkData: [100,105,102,108,115,112,118,122,119,126,131,128,134],
  },
  {
    id: 2, name: 'Dividend Picks', isPublic: false,
    stocks: ['JNJ', 'KO', 'PG', 'VZ', 'T', 'O', 'JPM'],
    changeStr: '-0.3%', changeUp: false,
    sparkData: [100,102,101,100,98,99,97,98,96,97,98,97,99],
  },
  {
    id: 3, name: 'S&P 500 Watch', isPublic: true,
    stocks: ['SPY', 'VOO', 'IVV'],
    changeStr: '+0.9%', changeUp: true,
    sparkData: [100,101,103,102,104,106,105,107,108,107,109,110,109],
  },
  {
    id: 4, name: 'Speculative', isPublic: false,
    stocks: [],
    changeStr: null, changeUp: null,
    sparkData: [],
  },
];

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [watchlists, setWatchlists] = useState<WatchlistItem[]>(INITIAL_WATCHLISTS);
  const [activeId, setActiveId] = useState<number | null>(null);

  const activeWatchlist = watchlists.find(w => w.id === activeId) ?? null;

  function openWatchlist(id: number) {
    setActiveId(id);
    setSidebarOpen(false);
  }

  function updateStocks(id: number, stocks: string[]) {
    setWatchlists(prev => prev.map(w => w.id === id ? { ...w, stocks } : w));
  }

  return (
    <div className="shell">
      <div
        className={`sidebar-overlay${sidebarOpen ? ' visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />
      <SideNav
        isOpen={sidebarOpen}
        watchlists={watchlists}
        onOpenWatchlist={openWatchlist}
        onGoHome={() => setActiveId(null)}
        activeId={activeId}
      />
      <div className="body">
        <Header onMenuClick={() => setSidebarOpen(v => !v)} />
        <main className="app-main">
          {activeWatchlist ? (
            <WatchlistPage
              watchlist={activeWatchlist}
              onBack={() => setActiveId(null)}
              onUpdateStocks={stocks => updateStocks(activeWatchlist.id, stocks)}
            />
          ) : (
            <HomePage watchlists={watchlists} onOpenWatchlist={openWatchlist} />
          )}
        </main>
      </div>
    </div>
  );
}

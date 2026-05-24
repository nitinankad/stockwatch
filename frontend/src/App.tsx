import { useState } from 'react';
import { useRouter } from './hooks/useRouter';
import { SideNav } from './components/layout/SideNav';
import { Header } from './components/layout/Header';
import { HomePage } from './pages/HomePage';
import { WatchlistPage } from './pages/WatchlistPage';
import { StockPage } from './pages/StockPage';
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
  const { route, navigate } = useRouter();

  function updateStocks(id: number, stocks: string[]) {
    setWatchlists(prev => prev.map(w => w.id === id ? { ...w, stocks } : w));
  }

  function toggleWatchlist(watchlistId: number, ticker: string) {
    setWatchlists(prev => prev.map(w => {
      if (w.id !== watchlistId) return w;
      const has = w.stocks.includes(ticker);
      return { ...w, stocks: has ? w.stocks.filter(s => s !== ticker) : [...w.stocks, ticker] };
    }));
  }

  function deleteWatchlist(id: number) {
    setWatchlists(prev => prev.filter(w => w.id !== id));
    navigate('/');
  }

  const activeWatchlist =
    route.page === 'watchlist' ? watchlists.find(w => w.id === route.id) ?? null : null;

  return (
    <div className="shell">
      <div
        className={`sidebar-overlay${sidebarOpen ? ' visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />
      <SideNav
        isOpen={sidebarOpen}
        watchlists={watchlists}
        navigate={navigate}
        activeRoute={route}
      />
      <div className="body">
        <Header
          onMenuClick={() => setSidebarOpen(v => !v)}
          watchlists={watchlists}
          navigate={navigate}
        />
        <main className="app-main">
          {route.page === 'stock' ? (
            <StockPage
              ticker={route.ticker}
              watchlists={watchlists}
              onBack={() => navigate('/')}
              onToggleWatchlist={toggleWatchlist}
            />
          ) : route.page === 'watchlist' && activeWatchlist ? (
            <WatchlistPage
              watchlist={activeWatchlist}
              onBack={() => navigate('/')}
              onUpdateStocks={stocks => updateStocks(activeWatchlist.id, stocks)}
              onDeleteWatchlist={() => deleteWatchlist(activeWatchlist.id)}
              navigate={navigate}
            />
          ) : (
            <HomePage watchlists={watchlists} navigate={navigate} />
          )}
        </main>
      </div>
    </div>
  );
}

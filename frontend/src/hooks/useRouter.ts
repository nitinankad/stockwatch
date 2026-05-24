import { useState, useEffect } from 'react';

export type Route =
  | { page: 'home' }
  | { page: 'watchlist'; id: number }
  | { page: 'stock'; ticker: string };

function parseRoute(): Route {
  const path = window.location.pathname;
  const stockMatch = path.match(/^\/stocks\/([A-Za-z.^]+)$/);
  if (stockMatch) return { page: 'stock', ticker: stockMatch[1].toUpperCase() };
  const watchlistMatch = path.match(/^\/watchlist\/(\d+)$/);
  if (watchlistMatch) return { page: 'watchlist', id: Number(watchlistMatch[1]) };
  return { page: 'home' };
}

export function useRouter() {
  const [route, setRoute] = useState<Route>(parseRoute);

  useEffect(() => {
    function onPop() { setRoute(parseRoute()); }
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  function navigate(path: string) {
    history.pushState(null, '', path);
    setRoute(parseRoute());
  }

  return { route, navigate };
}

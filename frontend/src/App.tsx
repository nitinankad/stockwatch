import { useState } from 'react';
import { SideNav } from './components/layout/SideNav';
import { Header } from './components/layout/Header';
import './App.css';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="shell">
      <div
        className={`sidebar-overlay${sidebarOpen ? ' visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />
      <SideNav isOpen={sidebarOpen} />
      <div className="body">
        <Header onMenuClick={() => setSidebarOpen(v => !v)} />
        <main className="app-main" />
      </div>
    </div>
  );
}

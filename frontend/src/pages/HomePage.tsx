const EDITOR_PICK = {
  title: "High-conviction tech plays for Q3",
  description:
    "A concentrated list of 4 names with strong earnings momentum, improving margins, and institutional accumulation heading into the back half of the year.",
  author: "Marcus Chen",
  followers: "1.2k followers",
  stocks: ["NVDA", "MSFT", "AAPL", "META"],
  chartData: [
    142, 145, 143, 148, 152, 149, 155, 158, 154, 161,
    165, 162, 168, 172, 170, 175, 179, 176, 182, 186,
    184, 189, 193, 191, 196, 201, 198, 204, 208, 211,
  ],
};

const TRENDING = [
  {
    initials: "SR", author: "Sofia Reyes", color: "#0ea5e9",
    title: "Dividend compounders I've held for 5+ years",
    description: "Boring but beautiful. These slow-movers have quietly tripled while everyone chased memes.",
    tickers: ["JNJ", "KO", "PG", "VZ"], followers: "843",
  },
  {
    initials: "AT", author: "Alex Tanner", color: "#8b5cf6",
    title: "Small-cap breakouts on my radar",
    description: "High risk, high reward setups forming on the weekly chart with volume confirmation.",
    tickers: ["AEHR", "IONQ", "BLNK"], followers: "2.1k",
  },
  {
    initials: "PK", author: "Priya K.", color: "#10b981",
    title: "The infrastructure supercycle watchlist",
    description: "Grid upgrades, data centers, water systems — the dull picks underpinning every hype trend.",
    tickers: ["PWR", "GTLS", "ARIS", "XYL"], followers: "631",
  },
];

const COMMUNITY = [
  { initials: "JM", author: "James M.", color: "#f59e0b", title: "Biotech moonshots", tickers: ["MRNA", "CRSP", "EDIT"], followers: "418" },
  { initials: "LW", author: "Lena W.", color: "#ef4444", title: "Rate-sensitive REITs to watch", tickers: ["O", "VTR", "SPG"], followers: "309" },
  { initials: "BN", author: "Ben N.", color: "#06b6d4", title: "EV & battery supply chain plays", tickers: ["LTHM", "ALB", "MP"], followers: "774" },
  { initials: "CL", author: "Carmen L.", color: "#ec4899", title: "Consumer staples in a stagflation scenario", tickers: ["CLX", "HRL", "MKC"], followers: "221" },
];

function EditorPickChart({ data }: { data: number[] }) {
  const w = 400;
  const h = 100;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = { t: 6, b: 6, l: 2, r: 2 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const pts = data.map((v, i) => {
    const x = pad.l + (i / (data.length - 1)) * innerW;
    const y = pad.t + (1 - (v - min) / range) * innerH;
    return [x, y] as [number, number];
  });

  const linePath = `M ${pts.map(([x, y]) => `${x},${y}`).join(' L ')}`;
  const areaPath = `${linePath} L ${pts[pts.length - 1][0]},${pad.t + innerH} L ${pad.l},${pad.t + innerH} Z`;

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="ep-chart">
      <defs>
        <linearGradient id="ep-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#16a34a" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#16a34a" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#ep-fill)" />
      <path d={linePath} fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function today() {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
  }).toUpperCase();
}

export function HomePage() {
  return (
    <div className="home-page">
      <div className="home-inner">
        <header className="home-header">
          <span className="home-date">{today()}</span>
          <h1 className="home-heading">
            <em>Watchlists</em> worth watching.
          </h1>
        </header>

        {/* Editor's Pick */}
        <section className="home-section">
          <div className="ep-card">
            <div className="ep-left">
              <span className="ep-badge">Editor's Pick</span>
              <h2 className="ep-title">{EDITOR_PICK.title}</h2>
              <p className="ep-desc">{EDITOR_PICK.description}</p>
              <span className="ep-author">by {EDITOR_PICK.author} · {EDITOR_PICK.followers}</span>
              <div className="ep-actions">
                <button className="ep-btn ep-btn-primary">Follow list</button>
                <button className="ep-btn ep-btn-secondary">View all</button>
              </div>
            </div>
            <div className="ep-right">
              <EditorPickChart data={EDITOR_PICK.chartData} />
              <div className="ep-chips">
                {EDITOR_PICK.stocks.map(sym => (
                  <span key={sym} className="ep-chip">{sym}</span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Trending */}
        <section className="home-section">
          <h3 className="section-heading">Trending this week</h3>
          <div className="trending-grid">
            {TRENDING.map(({ initials, author, title, description, tickers, followers, color }) => (
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
              </div>
            ))}
          </div>
        </section>

        {/* Community picks */}
        <section className="home-section">
          <h3 className="section-heading">From the community</h3>
          <div className="community-grid">
            {COMMUNITY.map(({ initials, author, color, title, tickers, followers }) => (
              <div key={author} className="community-card">
                <div className="community-card-top">
                  <div className="community-card-avatar" style={{ background: color }}>{initials}</div>
                  <span className="community-card-name">{author}</span>
                </div>
                <div className="community-card-title">{title}</div>
                <div className="community-card-footer">
                  <div className="community-card-tickers">
                    {tickers.map(sym => (
                      <span key={sym} className="community-card-chip">{sym}</span>
                    ))}
                  </div>
                  <span className="community-card-stat">{followers} followers</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

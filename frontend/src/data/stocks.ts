export type StockNews = {
  headline: string;
  source: string;
  timeAgo: string;
  sentiment: 'positive' | 'negative' | 'neutral';
};

export type StockStats = {
  marketCap: string;
  peRatio: string | null;
  volume: string;
  avgVolume: string;
  high52w: number;
  low52w: number;
  divYield: string | null;
  beta: string;
  eps: string | null;
  revenueTTM: string | null;
};

export type StockInfo = {
  ticker: string;
  company: string;
  price: number;
  change: number;
  changePct: number;
  priceUp: boolean;
  history: number[];
  sentiment: 'bullish' | 'bearish' | 'neutral';
  sentimentScore: number;
  sentimentSummary: string;
  news: StockNews[];
  stats: StockStats;
};

export const STOCK_DATABASE: Record<string, StockInfo> = {
  NVDA: {
    ticker: 'NVDA', company: 'NVIDIA Corporation',
    price: 891.26, change: 21.41, changePct: 2.46, priceUp: true,
    history: [820,832,825,841,855,848,862,878,871,884,876,891,885,903,897,912,908,921,916,928,922,934,929,941,935,948,942,956,951,891],
    sentiment: 'bullish', sentimentScore: 84,
    sentimentSummary: 'NVIDIA continues to lead the AI hardware buildout with Blackwell Ultra demand surging. Analysts broadly positive ahead of next earnings.',
    news: [
      { headline: "Nvidia's Blackwell Ultra chips ship ahead of schedule as hyperscaler demand hits records", source: 'Reuters', timeAgo: '2h', sentiment: 'positive' },
      { headline: "Jensen Huang: data center opportunity will reach $5T by 2030", source: 'Bloomberg', timeAgo: '5h', sentiment: 'positive' },
      { headline: "NVDA Q1 beats estimates — EPS $6.12 vs. $5.89 expected", source: 'WSJ', timeAgo: '1d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$2.18T', peRatio: '51.4', volume: '28.4M', avgVolume: '32.1M', high52w: 974.00, low52w: 462.77, divYield: '0.03%', beta: '1.68', eps: '$17.36', revenueTTM: '$130.4B' },
  },
  MSFT: {
    ticker: 'MSFT', company: 'Microsoft Corporation',
    price: 432.18, change: 5.34, changePct: 1.25, priceUp: true,
    history: [398,404,401,408,415,411,418,424,420,427,422,430,426,434,429,437,432,440,436,444,439,447,443,451,446,454,449,457,452,432],
    sentiment: 'bullish', sentimentScore: 78,
    sentimentSummary: 'Azure AI workloads are accelerating. Copilot+ is showing strong enterprise uptake. Dividend raise signals confidence in long-term cash flow.',
    news: [
      { headline: "Microsoft Azure AI workloads hit 45% of cloud revenue, analysts raise price targets", source: 'FT', timeAgo: '3h', sentiment: 'positive' },
      { headline: "Copilot+ PC adoption accelerating among enterprise customers, Microsoft says", source: 'CNBC', timeAgo: '6h', sentiment: 'positive' },
      { headline: "Microsoft raises dividend 12%, announces $60B buyback program", source: 'Reuters', timeAgo: '2d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$3.21T', peRatio: '34.8', volume: '18.2M', avgVolume: '21.4M', high52w: 468.35, low52w: 387.00, divYield: '0.72%', beta: '0.92', eps: '$12.41', revenueTTM: '$245.1B' },
  },
  AAPL: {
    ticker: 'AAPL', company: 'Apple Inc.',
    price: 211.43, change: -1.87, changePct: -0.88, priceUp: false,
    history: [225,222,224,220,217,219,215,213,216,212,214,210,212,209,211,208,210,207,209,206,208,205,207,204,206,203,205,213,209,211],
    sentiment: 'neutral', sentimentScore: 52,
    sentimentSummary: 'iPhone cycle tracking in-line with estimates. China recovery remains the key swing factor. Services growth is solid but hardware is under pressure.',
    news: [
      { headline: "Apple's Vision Pro 2 faces supply constraints ahead of summer launch", source: 'Bloomberg', timeAgo: '1h', sentiment: 'negative' },
      { headline: "iPhone 17 preorders tracking in-line; China recovery a key variable", source: 'Morgan Stanley', timeAgo: '4h', sentiment: 'neutral' },
      { headline: "Apple Services revenue grows 14% but hardware disappoints for second straight quarter", source: 'WSJ', timeAgo: '1d', sentiment: 'negative' },
    ],
    stats: { marketCap: '$3.18T', peRatio: '28.9', volume: '52.1M', avgVolume: '61.3M', high52w: 237.49, low52w: 196.71, divYield: '0.48%', beta: '1.24', eps: '$6.88', revenueTTM: '$391.0B' },
  },
  META: {
    ticker: 'META', company: 'Meta Platforms Inc.',
    price: 618.72, change: 12.05, changePct: 1.99, priceUp: true,
    history: [572,580,576,585,591,587,595,601,597,605,600,608,603,612,607,616,610,619,614,623,618,627,621,630,625,634,628,637,631,619],
    sentiment: 'bullish', sentimentScore: 79,
    sentimentSummary: "Meta's Llama 4 is dominating open-source AI benchmarks, boosting the ad platform's targeting capabilities. Reality Labs losses are narrowing ahead of Quest 4.",
    news: [
      { headline: "Meta's Llama 4 dominates open-source benchmarks; ad targeting sees major lift", source: 'TechCrunch', timeAgo: '2h', sentiment: 'positive' },
      { headline: "Reality Labs losses narrow to $3.1B as Quest 4 shipments begin", source: 'Bloomberg', timeAgo: '5h', sentiment: 'positive' },
      { headline: "Meta raises 2026 capex guidance to $75B to build AI infrastructure moat", source: 'FT', timeAgo: '1d', sentiment: 'neutral' },
    ],
    stats: { marketCap: '$1.56T', peRatio: '26.1', volume: '11.3M', avgVolume: '14.8M', high52w: 740.91, low52w: 414.50, divYield: '0.26%', beta: '1.41', eps: '$23.86', revenueTTM: '$162.0B' },
  },
  JNJ: {
    ticker: 'JNJ', company: 'Johnson & Johnson',
    price: 158.34, change: 0.86, changePct: 0.55, priceUp: true,
    history: [152,153,154,153,155,154,156,155,157,156,158,157,159,158,160,159,161,160,162,161,160,159,158,157,158,157,156,157,158,158],
    sentiment: 'neutral', sentimentScore: 58,
    sentimentSummary: 'Talc settlement clears a major legal overhang. MedTech segment is outperforming. Pharma pipeline is solid but lacks near-term blockbuster catalysts.',
    news: [
      { headline: "J&J talc litigation settlement finalized, clearing $8.9B legal overhang", source: 'Reuters', timeAgo: '4h', sentiment: 'positive' },
      { headline: "MedTech segment posts 7% organic growth, beats estimates for third consecutive quarter", source: 'Bloomberg', timeAgo: '1d', sentiment: 'positive' },
      { headline: "J&J reaffirms FY2026 EPS guidance of $10.50–$10.70", source: 'CNBC', timeAgo: '2d', sentiment: 'neutral' },
    ],
    stats: { marketCap: '$381.4B', peRatio: '15.8', volume: '7.4M', avgVolume: '8.9M', high52w: 167.24, low52w: 144.12, divYield: '3.18%', beta: '0.54', eps: '$9.98', revenueTTM: '$90.1B' },
  },
  KO: {
    ticker: 'KO', company: 'The Coca-Cola Company',
    price: 68.24, change: 0.41, changePct: 0.60, priceUp: true,
    history: [63,64,64,65,65,66,65,66,67,66,67,68,67,68,69,68,69,70,69,70,69,68,69,68,69,68,67,68,68,68],
    sentiment: 'bullish', sentimentScore: 71,
    sentimentSummary: 'Volume recovery in emerging markets is ahead of expectations. Pricing power remains intact. The Fairlife protein line is becoming a meaningful growth contributor.',
    news: [
      { headline: "Coca-Cola volumes rebound in emerging markets, pricing power remains intact", source: 'Reuters', timeAgo: '3h', sentiment: 'positive' },
      { headline: "KO expands Fairlife protein line to 14 new markets, early sales tracking above plan", source: 'Bloomberg', timeAgo: '6h', sentiment: 'positive' },
      { headline: "Berkshire increases KO stake by 2M shares in Q1 2026 filing", source: 'SEC', timeAgo: '1d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$293.8B', peRatio: '24.1', volume: '14.2M', avgVolume: '15.6M', high52w: 72.84, low52w: 60.23, divYield: '2.97%', beta: '0.61', eps: '$2.83', revenueTTM: '$46.5B' },
  },
  PG: {
    ticker: 'PG', company: 'Procter & Gamble Co.',
    price: 162.88, change: -0.54, changePct: -0.33, priceUp: false,
    history: [168,167,166,167,166,165,166,165,164,165,164,163,164,163,162,163,162,161,162,161,160,161,162,161,162,163,162,163,163,163],
    sentiment: 'neutral', sentimentScore: 50,
    sentimentSummary: 'Volume growth has stalled as premium pricing reaches its limits in developed markets. Organic sales of 3% met only the low end of guidance. Defensive positioning still appeals.',
    news: [
      { headline: "P&G volumes flat as premium pricing reaches limits in key markets", source: 'WSJ', timeAgo: '2h', sentiment: 'negative' },
      { headline: "Organic sales growth of 3% meets low end of guidance range", source: 'Bloomberg', timeAgo: '1d', sentiment: 'neutral' },
      { headline: "P&G announces $5B buyback program for fiscal 2026", source: 'CNBC', timeAgo: '2d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$382.1B', peRatio: '26.4', volume: '6.8M', avgVolume: '7.4M', high52w: 172.31, low52w: 154.28, divYield: '2.39%', beta: '0.52', eps: '$6.16', revenueTTM: '$83.9B' },
  },
  VZ: {
    ticker: 'VZ', company: 'Verizon Communications',
    price: 38.72, change: -0.63, changePct: -1.60, priceUp: false,
    history: [42,41,41,40,40,39,40,39,38,39,38,37,38,37,36,37,36,37,38,37,38,39,38,39,38,39,38,39,39,39],
    sentiment: 'bearish', sentimentScore: 31,
    sentimentSummary: 'Subscriber adds continue to miss estimates as T-Mobile aggressively takes market share. Fixed wireless growth is decelerating. High debt load remains a structural concern.',
    news: [
      { headline: "Verizon subscriber adds miss estimates for third straight quarter; T-Mobile takes share", source: 'Reuters', timeAgo: '1h', sentiment: 'negative' },
      { headline: "Fixed wireless access growth slows sharply to 8%, below 15% target", source: 'FT', timeAgo: '4h', sentiment: 'negative' },
      { headline: "Verizon debt load concerns analysts ahead of spectrum auction spending", source: 'Bloomberg', timeAgo: '2d', sentiment: 'negative' },
    ],
    stats: { marketCap: '$162.8B', peRatio: '9.4', volume: '18.4M', avgVolume: '21.2M', high52w: 44.73, low52w: 35.18, divYield: '6.60%', beta: '0.42', eps: '$4.12', revenueTTM: '$134.8B' },
  },
  T: {
    ticker: 'T', company: 'AT&T Inc.',
    price: 22.14, change: -0.38, changePct: -1.69, priceUp: false,
    history: [25,24,24,23,24,23,22,23,22,23,22,21,22,21,22,21,22,21,22,21,22,23,22,23,22,23,22,22,22,22],
    sentiment: 'bearish', sentimentScore: 28,
    sentimentSummary: "AT&T is facing rising competition, free cash flow pressure, and delayed fiber expansion. The dividend appears safe near-term but growth catalysts are limited.",
    news: [
      { headline: "AT&T free cash flow guidance lowered amid FirstNet cost overruns", source: 'WSJ', timeAgo: '2h', sentiment: 'negative' },
      { headline: "Subscriber churn ticks up as rivals offer aggressive promotional pricing", source: 'CNBC', timeAgo: '5h', sentiment: 'negative' },
      { headline: "AT&T delays fiber rollout expansion to 2027 citing supply constraints", source: 'Reuters', timeAgo: '1d', sentiment: 'negative' },
    ],
    stats: { marketCap: '$158.2B', peRatio: '12.1', volume: '38.4M', avgVolume: '44.1M', high52w: 27.48, low52w: 19.39, divYield: '7.99%', beta: '0.67', eps: '$1.83', revenueTTM: '$122.4B' },
  },
  SPY: {
    ticker: 'SPY', company: 'SPDR S&P 500 ETF Trust',
    price: 588.14, change: 4.92, changePct: 0.84, priceUp: true,
    history: [548,552,549,555,560,557,563,568,564,570,566,572,568,575,570,577,573,580,575,582,577,584,579,586,581,588,583,590,585,588],
    sentiment: 'bullish', sentimentScore: 72,
    sentimentSummary: 'S&P 500 on record territory as AI earnings beats and cooling inflation data support risk appetite. Fed signaling one cut in H2 2026 is broadly supportive.',
    news: [
      { headline: "S&P 500 hits record as AI earnings beats and cooling CPI fuel rally", source: 'Bloomberg', timeAgo: '1h', sentiment: 'positive' },
      { headline: "Fed signals one rate cut in H2 2026; markets rally broadly on dot plot", source: 'WSJ', timeAgo: '3h', sentiment: 'positive' },
      { headline: "Q1 2026 earnings season: 78% of S&P 500 companies beat EPS estimates", source: 'FactSet', timeAgo: '1d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$612.1B', peRatio: '22.4', volume: '68.2M', avgVolume: '74.1M', high52w: 613.24, low52w: 505.86, divYield: '1.38%', beta: '1.00', eps: null, revenueTTM: null },
  },
  VOO: {
    ticker: 'VOO', company: 'Vanguard S&P 500 ETF',
    price: 540.82, change: 4.51, changePct: 0.84, priceUp: true,
    history: [503,506,504,509,514,511,517,522,518,524,520,526,522,529,524,531,527,534,530,537,532,539,534,541,536,543,538,545,540,541],
    sentiment: 'bullish', sentimentScore: 70,
    sentimentSummary: 'Vanguard passive products continue to see record inflows. S&P 500 valuations are elevated but supported by strong earnings growth and AI productivity tailwinds.',
    news: [
      { headline: "Vanguard reports record $12B weekly inflow to VOO as passive investing accelerates", source: 'Reuters', timeAgo: '2h', sentiment: 'positive' },
      { headline: "S&P 500 valuations elevated but supported by earnings growth of 9% YoY", source: 'Bloomberg', timeAgo: '5h', sentiment: 'neutral' },
      { headline: "Index investors rewarded again as 92% of active funds underperform benchmarks", source: 'Morningstar', timeAgo: '2d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$582.4B', peRatio: '22.4', volume: '4.2M', avgVolume: '4.8M', high52w: 564.44, low52w: 465.12, divYield: '1.39%', beta: '1.00', eps: null, revenueTTM: null },
  },
  IVV: {
    ticker: 'IVV', company: 'iShares Core S&P 500 ETF',
    price: 541.96, change: 4.54, changePct: 0.84, priceUp: true,
    history: [504,507,505,510,515,512,518,523,519,525,521,527,523,530,525,532,528,535,531,538,533,540,535,542,537,544,539,546,541,542],
    sentiment: 'bullish', sentimentScore: 70,
    sentimentSummary: "BlackRock's core S&P 500 ETF is benefiting from the broad index rally. Institutional flows remain strong. Low expense ratio continues to attract long-term investors.",
    news: [
      { headline: "iShares IVV sees $4.2B weekly inflow amid broad market strength", source: 'BlackRock', timeAgo: '3h', sentiment: 'positive' },
      { headline: "BlackRock adds AI-driven factor overlays to core ETF research offerings", source: 'FT', timeAgo: '6h', sentiment: 'positive' },
      { headline: "S&P 500 dividend yield at 1.4%, near multi-year lows as valuations stretch", source: 'Bloomberg', timeAgo: '1d', sentiment: 'neutral' },
    ],
    stats: { marketCap: '$616.8B', peRatio: '22.4', volume: '3.8M', avgVolume: '4.2M', high52w: 565.14, low52w: 465.98, divYield: '1.38%', beta: '1.00', eps: null, revenueTTM: null },
  },
  AMZN: {
    ticker: 'AMZN', company: 'Amazon.com Inc.',
    price: 202.45, change: 3.12, changePct: 1.56, priceUp: true,
    history: [186,188,187,190,192,191,193,196,194,197,195,198,196,199,197,200,198,201,199,202,200,203,201,204,202,205,203,206,204,202],
    sentiment: 'bullish', sentimentScore: 76,
    sentimentSummary: 'AWS AI services are the primary growth driver. The advertising segment continues to outperform. Logistics efficiency gains are driving meaningful margin expansion.',
    news: [
      { headline: "AWS AI services revenue surges 42% YoY, becoming #1 revenue growth driver", source: 'Bloomberg', timeAgo: '2h', sentiment: 'positive' },
      { headline: "Amazon advertising hits $60B run rate, closing gap with Google and Meta", source: 'WSJ', timeAgo: '4h', sentiment: 'positive' },
      { headline: "Amazon logistics margin improves 4 points as delivery network matures", source: 'Reuters', timeAgo: '1d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$2.14T', peRatio: '41.2', volume: '34.8M', avgVolume: '38.4M', high52w: 242.47, low52w: 171.21, divYield: null, beta: '1.38', eps: '$4.91', revenueTTM: '$637.9B' },
  },
  GOOGL: {
    ticker: 'GOOGL', company: 'Alphabet Inc.',
    price: 178.32, change: 2.14, changePct: 1.21, priceUp: true,
    history: [164,166,165,167,169,168,170,172,171,173,172,174,173,175,174,176,175,177,176,178,177,179,178,180,179,181,180,182,181,178],
    sentiment: 'bullish', sentimentScore: 68,
    sentimentSummary: 'Google Search remains dominant. Gemini AI integration is boosting Search monetization. Cloud AI competition from AWS and Azure remains a headwind.',
    news: [
      { headline: "Google Search AI Mode sees 65% query growth as Gemini integration deepens", source: 'TechCrunch', timeAgo: '1h', sentiment: 'positive' },
      { headline: "Alphabet cloud revenue grows 28% but trails AWS and Azure in AI workloads", source: 'FT', timeAgo: '4h', sentiment: 'neutral' },
      { headline: "EU antitrust ruling on Google ad tech could cost up to $8B annually", source: 'Reuters', timeAgo: '1d', sentiment: 'negative' },
    ],
    stats: { marketCap: '$2.18T', peRatio: '21.8', volume: '22.4M', avgVolume: '26.1M', high52w: 207.56, low52w: 155.72, divYield: '0.51%', beta: '1.04', eps: '$8.18', revenueTTM: '$358.8B' },
  },
  TSLA: {
    ticker: 'TSLA', company: 'Tesla Inc.',
    price: 248.16, change: -5.34, changePct: -2.11, priceUp: false,
    history: [290,285,280,278,275,272,270,268,265,263,260,258,255,260,258,262,260,265,263,268,265,262,258,255,252,255,252,250,249,248],
    sentiment: 'bearish', sentimentScore: 38,
    sentimentSummary: 'EV demand is softening in the US as competition intensifies from BYD and legacy automakers. FSD progress is slower than promised. Robotaxi delays are weighing on sentiment.',
    news: [
      { headline: "Tesla Q1 deliveries miss expectations as EV price cuts fail to spark demand", source: 'Reuters', timeAgo: '2h', sentiment: 'negative' },
      { headline: "Cybertruck recall expanded to 46,000 vehicles over software defect", source: 'Bloomberg', timeAgo: '5h', sentiment: 'negative' },
      { headline: "Tesla FSD v14 launch delayed to Q3, Robotaxi rollout pushed to 2027", source: 'CNBC', timeAgo: '1d', sentiment: 'negative' },
    ],
    stats: { marketCap: '$796.4B', peRatio: '83.2', volume: '124.8M', avgVolume: '138.2M', high52w: 362.44, low52w: 182.00, divYield: null, beta: '2.34', eps: '$2.98', revenueTTM: '$95.1B' },
  },
  JPM: {
    ticker: 'JPM', company: 'JPMorgan Chase & Co.',
    price: 248.76, change: 2.43, changePct: 0.99, priceUp: true,
    history: [232,234,233,236,238,237,239,241,240,242,241,243,242,244,243,245,244,246,245,247,246,248,247,249,248,250,249,251,250,249],
    sentiment: 'bullish', sentimentScore: 73,
    sentimentSummary: 'JPMorgan continues to take market share across investment banking and consumer banking. Jamie Dimon remains cautious on the macro but is bullish on AI-driven productivity.',
    news: [
      { headline: "JPMorgan investment banking fees surge 38% as M&A market recovers", source: 'FT', timeAgo: '2h', sentiment: 'positive' },
      { headline: "Jamie Dimon warns of fiscal deficit risk but says bank is well-positioned", source: 'Bloomberg', timeAgo: '4h', sentiment: 'neutral' },
      { headline: "JPM raises quarterly dividend to $1.40, announces $30B buyback", source: 'Reuters', timeAgo: '2d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$714.2B', peRatio: '13.8', volume: '8.4M', avgVolume: '9.2M', high52w: 268.48, low52w: 203.14, divYield: '2.25%', beta: '1.12', eps: '$18.02', revenueTTM: '$178.2B' },
  },
  MRNA: {
    ticker: 'MRNA', company: 'Moderna Inc.',
    price: 44.82, change: -1.24, changePct: -2.69, priceUp: false,
    history: [55,53,54,52,51,52,50,51,49,50,48,49,47,48,46,47,45,46,44,45,44,45,44,46,45,46,45,46,45,45],
    sentiment: 'bearish', sentimentScore: 35,
    sentimentSummary: 'COVID revenue has nearly dried up. Pipeline catalysts including oncology mRNA and RSV are taking longer than expected. Cash runway is a concern without a major approval.',
    news: [
      { headline: "Moderna oncology mRNA program shows mixed Phase 2 results", source: 'BioPharma Dive', timeAgo: '1h', sentiment: 'negative' },
      { headline: "COVID vaccine revenue falls 78% YoY; Moderna lowers FY guidance", source: 'Reuters', timeAgo: '3h', sentiment: 'negative' },
      { headline: "RSV vaccine FDA approval timeline extends to Q4 2026 after additional data request", source: 'Bloomberg', timeAgo: '1d', sentiment: 'negative' },
    ],
    stats: { marketCap: '$14.2B', peRatio: null, volume: '14.4M', avgVolume: '18.2M', high52w: 84.38, low52w: 28.04, divYield: null, beta: '1.84', eps: '-$8.24', revenueTTM: '$3.2B' },
  },
  CRSP: {
    ticker: 'CRSP', company: 'CRISPR Therapeutics AG',
    price: 58.34, change: 2.18, changePct: 3.88, priceUp: true,
    history: [48,49,50,49,51,52,51,53,54,53,55,56,55,57,56,58,57,59,58,60,59,58,57,58,59,58,59,60,59,58],
    sentiment: 'neutral', sentimentScore: 57,
    sentimentSummary: 'Casgevy commercial launch is progressing but slowly. Gene editing is a long-term opportunity. Near-term revenue visibility is limited and profitability remains years away.',
    news: [
      { headline: "Casgevy sickle cell therapy enrollment reaches 500 patients globally", source: 'Reuters', timeAgo: '2h', sentiment: 'positive' },
      { headline: "CRISPR Therapeutics and Vertex expand Casgevy manufacturing capacity", source: 'Bloomberg', timeAgo: '5h', sentiment: 'positive' },
      { headline: "CRSP burns $82M in cash in Q1 as commercial launch costs ramp", source: 'BioPharma Dive', timeAgo: '1d', sentiment: 'negative' },
    ],
    stats: { marketCap: '$4.8B', peRatio: null, volume: '2.1M', avgVolume: '2.8M', high52w: 82.44, low52w: 41.38, divYield: null, beta: '1.96', eps: '-$5.14', revenueTTM: '$0.9B' },
  },
  AEHR: {
    ticker: 'AEHR', company: 'Aehr Test Systems',
    price: 18.42, change: 0.84, changePct: 4.78, priceUp: true,
    history: [14,14,15,15,16,15,16,17,16,17,17,18,17,18,18,19,18,19,18,19,18,19,18,19,18,19,19,18,18,18],
    sentiment: 'neutral', sentimentScore: 60,
    sentimentSummary: 'Aehr Test benefits from growing silicon carbide wafer testing demand driven by EV adoption. Revenue visibility is improving but the customer base remains concentrated.',
    news: [
      { headline: "Aehr Test wins new SiC testing contract with major automotive chipmaker", source: 'Globe Newswire', timeAgo: '3h', sentiment: 'positive' },
      { headline: "AEHR Q3 revenue grows 28% driven by EV SiC demand recovery", source: 'CNBC', timeAgo: '1d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$0.72B', peRatio: '28.4', volume: '1.4M', avgVolume: '1.8M', high52w: 32.48, low52w: 11.24, divYield: null, beta: '2.42', eps: '$0.65', revenueTTM: '$104.2M' },
  },
  IONQ: {
    ticker: 'IONQ', company: 'IonQ Inc.',
    price: 32.18, change: 1.42, changePct: 4.62, priceUp: true,
    history: [24,25,24,26,27,26,28,29,28,30,29,31,30,32,31,33,32,33,32,34,33,34,33,34,33,34,33,33,32,32],
    sentiment: 'bullish', sentimentScore: 65,
    sentimentSummary: 'IonQ is positioning as a pure-play quantum computing leader. Government contracts are providing revenue stability. Commercial revenue remains nascent but growing.',
    news: [
      { headline: "IonQ awarded $54M U.S. Air Force quantum networking contract", source: 'Reuters', timeAgo: '1h', sentiment: 'positive' },
      { headline: "IonQ Forte system achieves record 35 algorithmic qubits", source: 'BusinessWire', timeAgo: '4h', sentiment: 'positive' },
      { headline: "IonQ Q1 revenue of $7.6M misses estimates; cash burn accelerates", source: 'Bloomberg', timeAgo: '2d', sentiment: 'negative' },
    ],
    stats: { marketCap: '$7.4B', peRatio: null, volume: '8.4M', avgVolume: '12.1M', high52w: 48.88, low52w: 16.44, divYield: null, beta: '2.84', eps: '-$0.82', revenueTTM: '$43.1M' },
  },
  BLNK: {
    ticker: 'BLNK', company: 'Blink Charging Co.',
    price: 3.84, change: -0.22, changePct: -5.42, priceUp: false,
    history: [6,5,5,5,5,4,5,4,4,5,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4],
    sentiment: 'bearish', sentimentScore: 22,
    sentimentSummary: 'Blink Charging faces an existential cash flow challenge. Utilization rates remain low, and the competitive EV charging landscape is intensifying from Tesla and ChargePoint.',
    news: [
      { headline: "Blink Charging raises going concern warning as cash burn continues", source: 'Reuters', timeAgo: '2h', sentiment: 'negative' },
      { headline: "BLNK Q1 revenue grows 12% but gross margins remain deeply negative", source: 'Bloomberg', timeAgo: '6h', sentiment: 'negative' },
      { headline: "Blink Charging explores strategic alternatives including asset sales", source: 'WSJ', timeAgo: '1d', sentiment: 'neutral' },
    ],
    stats: { marketCap: '$0.18B', peRatio: null, volume: '4.8M', avgVolume: '6.4M', high52w: 10.44, low52w: 2.18, divYield: null, beta: '2.12', eps: '-$2.44', revenueTTM: '$68.4M' },
  },
  PWR: {
    ticker: 'PWR', company: 'Quanta Services Inc.',
    price: 312.44, change: 4.18, changePct: 1.36, priceUp: true,
    history: [288,291,290,294,297,295,299,302,300,304,302,306,304,308,306,310,308,312,310,314,312,315,313,316,314,317,315,318,316,312],
    sentiment: 'bullish', sentimentScore: 77,
    sentimentSummary: 'Quanta Services is a direct beneficiary of grid modernization and data center buildout. Backlog is at record levels and margins are expanding on scale.',
    news: [
      { headline: "Quanta Services wins $2.4B grid modernization contract from Southeast utility", source: 'Reuters', timeAgo: '2h', sentiment: 'positive' },
      { headline: "PWR backlog hits record $33B as data center power infrastructure demand surges", source: 'Bloomberg', timeAgo: '5h', sentiment: 'positive' },
      { headline: "Quanta Services raises FY2026 EPS guidance to $9.40–$9.80", source: 'CNBC', timeAgo: '1d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$43.2B', peRatio: '34.8', volume: '1.8M', avgVolume: '2.1M', high52w: 352.44, low52w: 208.18, divYield: '0.13%', beta: '1.34', eps: '$8.98', revenueTTM: '$24.1B' },
  },
  O: {
    ticker: 'O', company: 'Realty Income Corp.',
    price: 54.82, change: -0.36, changePct: -0.65, priceUp: false,
    history: [58,57,57,56,57,56,55,56,55,56,55,54,55,54,55,54,55,54,55,55,55,54,55,54,55,55,55,55,55,55],
    sentiment: 'neutral', sentimentScore: 53,
    sentimentSummary: "Realty Income's monthly dividend is durable but growth is constrained by higher-for-longer rates making REIT acquisitions harder to underwrite. Portfolio quality is solid.",
    news: [
      { headline: "Realty Income declares 128th consecutive monthly dividend increase", source: 'PRNewswire', timeAgo: '4h', sentiment: 'positive' },
      { headline: "O acquisition pace slows as cap rate compression limits deal economics", source: 'Bloomberg', timeAgo: '1d', sentiment: 'negative' },
      { headline: "Realty Income expands European portfolio with €800M gaming property deal", source: 'FT', timeAgo: '2d', sentiment: 'positive' },
    ],
    stats: { marketCap: '$54.2B', peRatio: '37.1', volume: '6.8M', avgVolume: '7.4M', high52w: 63.84, low52w: 48.12, divYield: '5.94%', beta: '0.82', eps: '$1.48', revenueTTM: '$5.4B' },
  },
};

export const SEARCH_LIST = Object.values(STOCK_DATABASE).map(s => ({
  ticker: s.ticker,
  company: s.company,
}));

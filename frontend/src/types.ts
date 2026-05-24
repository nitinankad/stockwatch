export type WatchlistItem = {
  id: number;
  name: string;
  isPublic: boolean;
  stocks: string[];
  changeStr: string | null;
  changeUp: boolean | null;
  sparkData: number[];
};

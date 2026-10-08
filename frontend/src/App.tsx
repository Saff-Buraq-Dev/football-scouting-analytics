import { Link, Route, Routes } from "react-router-dom";
import { DataAttribution } from "./components/DataAttribution";
import { ComparePage } from "./pages/ComparePage";
import { MatchPage } from "./pages/MatchPage";
import { MatchesPage } from "./pages/MatchesPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ScoutingPage } from "./pages/ScoutingPage";
import { TeamProfilePage } from "./pages/TeamProfilePage";
import { TeamsPage } from "./pages/TeamsPage";
import { SearchPage } from "./pages/SearchPage";

function PitchMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="2.5" y="4.5" width="19" height="15" rx="2" />
      <line x1="12" y1="4.5" x2="12" y2="19.5" />
      <circle cx="12" cy="12" r="2.8" />
    </svg>
  );
}

export function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <PitchMark />
          Scouting Analytics <small>player-season profiles</small>
        </Link>
        <nav className="topnav">
          <Link to="/">Search</Link>
          <Link to="/scouting">Scouting</Link>
          <Link to="/compare">Compare</Link>
          <Link to="/teams">Teams</Link>
          <Link to="/matches">Matches</Link>
          <span className="topbar-meta">2015/16 · Premier League, La Liga, Serie A, Ligue 1</span>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/players/:playerId/seasons/:seasonId" element={<ProfilePage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/scouting" element={<ScoutingPage />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="/matches" element={<MatchesPage />} />
          <Route path="/matches/:matchId" element={<MatchPage />} />
          <Route path="/teams/:teamId/seasons/:seasonId" element={<TeamProfilePage />} />
        </Routes>
      </main>
      <footer className="footer">
        <DataAttribution />
        <span>Methodology: docs/FOOTBALL_ANALYTICS.md</span>
      </footer>
    </div>
  );
}

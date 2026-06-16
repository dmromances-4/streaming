import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { BrowsePage } from "./pages/BrowsePage";
import { HomePage } from "./pages/HomePage";
import { LivePage } from "./pages/LivePage";
import { LiveWatchPage } from "./pages/LiveWatchPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TitlePage } from "./pages/TitlePage";
import { WatchEpisodePage } from "./pages/WatchEpisodePage";
import { WatchMoviePage } from "./pages/WatchMoviePage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="browse" element={<BrowsePage />} />
        <Route path="live" element={<LivePage />} />
        <Route path="live/:channelId" element={<LiveWatchPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="title/:id" element={<TitlePage />} />
        <Route path="watch/:episodeId" element={<WatchEpisodePage />} />
        <Route path="watch/movie/:id" element={<WatchMoviePage />} />
      </Route>
    </Routes>
  );
}

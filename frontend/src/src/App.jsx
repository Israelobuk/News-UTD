import { useCallback, useEffect, useMemo, useState } from "react";
import DashboardApp from "./DashboardApp";
import HomePage from "./components/HomePage";

const DASHBOARD_PATH = "/monitor";
const HOME_PATH = "/";

function normalizePath(pathname) {
  return pathname.startsWith(DASHBOARD_PATH) ? DASHBOARD_PATH : HOME_PATH;
}

function App() {
  const [currentPath, setCurrentPath] = useState(() => normalizePath(window.location.pathname));

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(normalizePath(window.location.pathname));
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((nextPath) => {
    const normalized = normalizePath(nextPath);
    if (window.location.pathname !== normalized) {
      window.history.pushState({}, "", normalized);
    }
    setCurrentPath(normalized);
  }, []);

  const goHome = useCallback(() => navigate(HOME_PATH), [navigate]);
  const goDashboard = useCallback(() => navigate(DASHBOARD_PATH), [navigate]);

  const isDashboard = useMemo(
    () => currentPath === DASHBOARD_PATH,
    [currentPath]
  );

  if (isDashboard) {
    return <DashboardApp onNavigateHome={goHome} />;
  }

  return <HomePage onEnterDashboard={goDashboard} />;
}

export default App;

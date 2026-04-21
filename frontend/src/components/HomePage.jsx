import { useEffect, useMemo, useState } from "react";

const NEWS_TICKER_ITEMS = [
  "BREAKING HEADLINES",
  "MACRO NEWSWIRE",
  "EARNINGS ALERTS",
  "FED COMMENTARY",
  "CPI WATCH",
  "RATE CUT ODDS",
  "SECTOR ROTATION",
  "RISK SENTIMENT",
  "OVERNIGHT MARKETS",
  "GLOBAL EQUITIES",
  "CRYPTO HEADLINES",
  "ENERGY UPDATE",
  "TREASURY YIELDS",
  "MARKET MOVERS",
  "NEWS IMPACT SCORE",
  "LIVE SIGNAL FEED",
  "THEME CLUSTERING",
  "WATCHLIST FLOW",
];

function resolveBackendBaseUrl() {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  const isLocalDev = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  if (isLocalDev) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return `${window.location.protocol}//${window.location.host}/_/backend`;
}

function formatNumber(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return new Intl.NumberFormat("en-US").format(value);
}

function TickerRail({ items, reverse = false }) {
  const trackClassName = reverse ? "ticker-track reverse" : "ticker-track";
  return (
    <div className={trackClassName}>
      <div className="ticker-segment">
        {items.map((item, index) => (
          <span key={`front-${item}-${index}`}>{item}</span>
        ))}
      </div>
      <div className="ticker-segment" aria-hidden="true">
        {items.map((item, index) => (
          <span key={`back-${item}-${index}`}>{item}</span>
        ))}
      </div>
    </div>
  );
}

function HomePage({ onEnterDashboard }) {
  const [health, setHealth] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const apiBaseUrl = useMemo(() => resolveBackendBaseUrl(), []);

  useEffect(() => {
    const controller = new AbortController();

    const loadOverview = async () => {
      try {
        setLoading(true);
        setError("");
        const [healthResponse, analyticsResponse] = await Promise.all([
          fetch(`${apiBaseUrl}/health`, { signal: controller.signal }),
          fetch(`${apiBaseUrl}/api/analytics/summary`, { signal: controller.signal }),
        ]);

        if (!healthResponse.ok) {
          throw new Error(`health check failed: ${healthResponse.status}`);
        }

        const healthPayload = await healthResponse.json();
        setHealth(healthPayload);

        if (analyticsResponse.ok) {
          const analyticsPayload = await analyticsResponse.json();
          setAnalytics(analyticsPayload);
        } else {
          setAnalytics(null);
        }
      } catch (fetchError) {
        if (fetchError?.name !== "AbortError") {
          setError("Unable to load NewsUTD backend overview.");
        }
      } finally {
        setLoading(false);
      }
    };

    loadOverview();
    return () => controller.abort();
  }, [apiBaseUrl]);

  const totalPosts = analytics?.totals?.posts ?? 0;
  const averageSignal = analytics?.totals?.average_signal_score ?? 0;
  const cacheSource = health?.cache_source || analytics?.cache_source || "live";
  const watchedThemes = Array.isArray(health?.subreddits) ? health.subreddits : [];

  return (
    <div className="home-shell">
      <div className="ticker ticker-top" aria-hidden="true">
        <TickerRail items={NEWS_TICKER_ITEMS} />
      </div>

      <main className="hero" role="main">
        <section className="brand-block" aria-label="NewsUTD homepage intro">
          <p className="eyebrow">Market Signal Monitor</p>
          <h1 className="brand-name">
            <span className="boxed-letter" aria-hidden="true">
              <span className="boxed-letter-glyph">N</span>
            </span>
            <span className="word-tail">EWS-UTD</span>
          </h1>
          <p className="tagline">
            Catch market-moving narrative shifts before the tape fully reacts.
          </p>

          <section className="action-row">
            <button
              id="enter-btn"
              className="enter-btn"
              type="button"
              onClick={onEnterDashboard}
            >
              Enter Signal Console
            </button>
            <p className="helper">
              {loading ? "Syncing context..." : `Cache source: ${cacheSource}`}
            </p>
          </section>

          {error ? <p className="home-error">{error}</p> : null}

          <section className="metric-row">
            <article className="metric-chip">
              <p className="metric-label">Signals Cached</p>
              <p className="metric-value">{formatNumber(totalPosts)}</p>
            </article>
            <article className="metric-chip">
              <p className="metric-label">Avg Signal Score</p>
              <p className="metric-value">
                {averageSignal ? averageSignal.toFixed(2) : "--"}
              </p>
            </article>
            <article className="metric-chip">
              <p className="metric-label">Tracked Themes</p>
              <p className="metric-value">{watchedThemes.length || "--"}</p>
            </article>
          </section>

          <section className="watch-stack">
            <p className="watch-label">Current themes</p>
            <div className="watch-grid">
              {(watchedThemes.length ? watchedThemes : ["stocks", "investing", "economics"]).map((theme) => (
                <span key={theme}>{theme}</span>
              ))}
            </div>
          </section>
        </section>
      </main>

      <div className="ticker ticker-bottom" aria-hidden="true">
        <TickerRail items={NEWS_TICKER_ITEMS} />
      </div>
    </div>
  );
}

export default HomePage;

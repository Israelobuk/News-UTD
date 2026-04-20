import SearchSubreddit from "./SearchSubreddit";
import SubredditChip from "./SubredditChip";
import SignalFilters from "./SignalFilters";

function Sidebar({
  onNavigateHome,
  activeAlert,
  totalSignals,
  watchingSubreddits,
  onAddSubreddit,
  onRemoveSubreddit,
  filters,
  onChangeFilters,
  onResetFilters,
  filterResultCount,
  filterTotalCount,
}) {
  return (
    <aside className="dashboard-sidebar">
      <div className="sidebar-mainrow">
        <div className="sidebar-mainrow__left">
          <button
            type="button"
            className="sidebar-home-link"
            onClick={onNavigateHome}
          >
            NewsUTD Home
          </button>
        </div>

        <div className="sidebar-search">
          <SearchSubreddit
            watchingSubreddits={watchingSubreddits}
            onAdd={onAddSubreddit}
          />
        </div>

        <section className="sidebar-section sidebar-section--stats">
          <div className="sidebar-metrics">
            <div className="sidebar-metric">
              <span className="sidebar-metric__value">{totalSignals}</span>
              <span className="sidebar-metric__label">Signals</span>
            </div>
            <div className="sidebar-metric">
              <span className="sidebar-metric__value">{activeAlert ? 1 : 0}</span>
              <span className="sidebar-metric__label">Active</span>
            </div>
          </div>
        </section>
      </div>

      <section className="sidebar-section sidebar-section--watching">
        <div className="sidebar-watchlist-header">
          <p className="sidebar-panel__label">Watching</p>
          <span className="sidebar-watchlist-count">{watchingSubreddits.length}</span>
        </div>
        <div className="sidebar-tags">
          {watchingSubreddits.map((subreddit) => (
            <SubredditChip
              key={subreddit}
              name={subreddit}
              onRemove={onRemoveSubreddit}
            />
          ))}
        </div>
      </section>

      <SignalFilters
        filters={filters}
        onChange={onChangeFilters}
        onReset={onResetFilters}
        resultCount={filterResultCount}
        totalCount={filterTotalCount}
      />
    </aside>
  );
}

export default Sidebar;

import { useCallback, useEffect, useRef, useState } from "react";

function resolveApiBaseUrl() {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, "");
  }

  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/+$/, "");
  }

  return window.location.origin.replace(/\/+$/, "");
}

function resolveWebSocketUrl() {
  if (import.meta.env.VITE_WS_BASE_URL) {
    return `${import.meta.env.VITE_WS_BASE_URL.replace(/\/+$/, "")}/ws/alerts`;
  }

  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }

  if (import.meta.env.VITE_ALERT_WS_URL) {
    return import.meta.env.VITE_ALERT_WS_URL;
  }

  return `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/alerts`;
}

const API_BASE_URL = resolveApiBaseUrl();
const WS_URL = resolveWebSocketUrl();

const CONNECT_TIMEOUT_MS = 5000;
const HEARTBEAT_MS = 20000;
const HEARTBEAT_TIMEOUT_MS = 30000;
const INITIAL_RECONNECT_MS = 2000;
const MAX_RECONNECT_MS = 15000;
const MAX_SIGNAL_HISTORY = 250;

function toSlug(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 80);
}

function buildCanonicalPostUrl({ subreddit, postId, title }) {
  const safeSub = String(subreddit || "all").replace(/^r\//i, "").trim() || "all";
  const safeId = String(postId || "").trim() || "unknown";
  const slug = toSlug(title) || "post";
  return `https://reddit.com/r/${safeSub}/comments/${safeId}/${slug}/`;
}

function buildSubredditUrl(subreddit) {
  const safeSub = String(subreddit || "all").replace(/^r\//i, "").trim() || "all";
  return `https://reddit.com/r/${safeSub}/`;
}

function normalizePostUrl(postUrlCandidate, fallback, subredditFallback) {
  if (postUrlCandidate) {
    try {
      const parsed = new URL(postUrlCandidate, "https://reddit.com");
      const host = parsed.hostname.toLowerCase();
      const isRedditHost =
        host === "reddit.com" ||
        host === "www.reddit.com" ||
        host.endsWith(".reddit.com");
      const hasCommentsPath = parsed.pathname.includes("/comments/");
      if (isRedditHost && hasCommentsPath) {
        return `https://reddit.com${parsed.pathname}${parsed.search}${parsed.hash}`;
      }

      if (isRedditHost) {
        return subredditFallback;
      }
    } catch {
      // fall through
    }
  }

  return fallback;
}

function normalizeSignal(signal) {
  const post = signal?.post || {};
  const fallbackId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const postId = post.id || fallbackId;
  const canonicalPostUrl = buildCanonicalPostUrl({
    subreddit: post.subreddit,
    postId,
    title: post.title,
  });
  const subredditUrl = buildSubredditUrl(post.subreddit);

  const postUrl = normalizePostUrl(
    post.post_url || post.permalink,
    canonicalPostUrl,
    subredditUrl
  );

  return {
    id: signal?.signal_id || fallbackId,
    postId,
    title: post.title || "Untitled post",
    subreddit: String(post.subreddit || "unknown").toLowerCase(),
    username: post.author || post.username || "unknown",
    upvotes: post.upvotes ?? 0,
    comments: post.comment_count ?? 0,
    image: post.image || post.thumbnail_url || null,
    link: post.article_link || postUrl,
    post_url: postUrl,
    timestamp: post.timestamp || new Date().toISOString(),
    signalScore: signal?.signal_score ?? post.signal_score ?? 0,
    reasons: Array.isArray(signal?.reasons) ? signal.reasons : [],
  };
}

function normalizeApiPost(post) {
  const fallbackId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const postId = post?.id || fallbackId;
  const canonicalPostUrl = buildCanonicalPostUrl({
    subreddit: post?.subreddit,
    postId,
    title: post?.title,
  });
  const subredditUrl = buildSubredditUrl(post?.subreddit);

  const postUrl = normalizePostUrl(
    post?.post_url || post?.permalink,
    canonicalPostUrl,
    subredditUrl
  );

  return {
    id: postId,
    postId,
    title: post?.title || "Untitled post",
    subreddit: String(post?.subreddit || "unknown").toLowerCase(),
    username: post?.author || post?.username || "unknown",
    upvotes: post?.upvotes ?? 0,
    comments: post?.comment_count ?? post?.comments ?? 0,
    image: post?.image || post?.thumbnail_url || null,
    link: post?.article_link || postUrl,
    post_url: postUrl,
    timestamp: post?.timestamp || new Date().toISOString(),
    signalScore: post?.signal_score ?? 0,
    reasons: [],
  };
}

export function useSignalStream() {
  const [signals, setSignals] = useState([]);
  const [streamError, setStreamError] = useState("");

  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const heartbeatTimerRef = useRef(null);
  const heartbeatTimeoutRef = useRef(null);
  const connectTimeoutRef = useRef(null);
  const isUnmountedRef = useRef(false);
  const reconnectAttemptRef = useRef(0);
  const signalIdsRef = useRef(new Set());
  const signalsRef = useRef([]);

  const applySignals = useCallback((items) => {
    const normalized = items.slice(0, MAX_SIGNAL_HISTORY);
    signalsRef.current = normalized;
    signalIdsRef.current = new Set(normalized.map((item) => item.id));
    setSignals(normalized);
  }, []);

  const loadLatestSignals = useCallback(async () => {
    const response = await fetch(`${API_BASE_URL}/api/signals/latest`);
    if (!response.ok) {
      throw new Error(`Failed to fetch latest signals: ${response.status}`);
    }

    const data = await response.json();
    const posts = Array.isArray(data?.posts) ? data.posts : [];
    const normalizedPosts = posts.map(normalizeApiPost);

    if (normalizedPosts.length) {
      applySignals(normalizedPosts);
      setStreamError("");
    } else if (!signalsRef.current.length) {
      setStreamError("No signals available yet.");
    }

    return data;
  }, [applySignals]);

  const connectSocket = useCallback(() => {
    const clearSocketTimers = () => {
      if (heartbeatTimerRef.current) {
        window.clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
      if (heartbeatTimeoutRef.current) {
        window.clearTimeout(heartbeatTimeoutRef.current);
        heartbeatTimeoutRef.current = null;
      }
      if (connectTimeoutRef.current) {
        window.clearTimeout(connectTimeoutRef.current);
        connectTimeoutRef.current = null;
      }
    };

    const scheduleReconnect = () => {
      if (isUnmountedRef.current) {
        return;
      }

      const delay = Math.min(
        INITIAL_RECONNECT_MS * (2 ** reconnectAttemptRef.current),
        MAX_RECONNECT_MS
      );

      reconnectAttemptRef.current += 1;

      reconnectTimerRef.current = window.setTimeout(() => {
        openSocket();
      }, delay);
    };

    const openSocket = () => {
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      clearSocketTimers();

      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      connectTimeoutRef.current = window.setTimeout(() => {
        if (socket.readyState !== WebSocket.OPEN) {
          socket.close();
        }
      }, CONNECT_TIMEOUT_MS);

      socket.onopen = () => {
        reconnectAttemptRef.current = 0;

        if (connectTimeoutRef.current) {
          window.clearTimeout(connectTimeoutRef.current);
          connectTimeoutRef.current = null;
        }

        if (!signalsRef.current.length) {
          setStreamError("");
        }

        const resetHeartbeatTimeout = () => {
          if (heartbeatTimeoutRef.current) {
            window.clearTimeout(heartbeatTimeoutRef.current);
          }

          heartbeatTimeoutRef.current = window.setTimeout(() => {
            if (socket.readyState === WebSocket.OPEN) {
              socket.close();
            }
          }, HEARTBEAT_TIMEOUT_MS);
        };

        resetHeartbeatTimeout();

        heartbeatTimerRef.current = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send("ping");
            resetHeartbeatTimeout();
          }
        }, HEARTBEAT_MS);
      };

      socket.onerror = () => {
        if (!signalsRef.current.length) {
          setStreamError("Signal stream temporarily unavailable.");
        }
      };

      socket.onclose = () => {
        if (socketRef.current === socket) {
          socketRef.current = null;
        }

        clearSocketTimers();

        if (!signalsRef.current.length) {
          setStreamError("Signal stream temporarily unavailable.");
        }

        if (!isUnmountedRef.current) {
          scheduleReconnect();
        }
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message?.type === "hello") {
            const posts = Array.isArray(message?.payload?.posts) ? message.payload.posts : [];
            if (posts.length) {
              applySignals(posts.map(normalizeApiPost));
              setStreamError("");
            }
            return;
          }

          if (message?.type === "posts_snapshot") {
            const posts = Array.isArray(message?.payload?.posts) ? message.payload.posts : [];
            if (posts.length) {
              applySignals(posts.map(normalizeApiPost));
              setStreamError("");
            } else if (!signalsRef.current.length) {
              setStreamError("No signals available yet.");
            }
            return;
          }

          if (message?.type === "pong") {
            if (heartbeatTimeoutRef.current) {
              window.clearTimeout(heartbeatTimeoutRef.current);
            }

            heartbeatTimeoutRef.current = window.setTimeout(() => {
              if (socket.readyState === WebSocket.OPEN) {
                socket.close();
              }
            }, HEARTBEAT_TIMEOUT_MS);

            return;
          }

          if (message?.type !== "signal" || !message?.payload) {
            return;
          }

          const nextSignal = normalizeSignal(message.payload);

          if (signalIdsRef.current.has(nextSignal.id)) {
            return;
          }

          const next = [nextSignal, ...signalsRef.current].slice(0, MAX_SIGNAL_HISTORY);
          applySignals(next);
          setStreamError("");
        } catch (error) {
          console.error("WebSocket message parse error:", error);
          if (!signalsRef.current.length) {
            setStreamError("Signal stream temporarily unavailable.");
          }
        }
      };
    };

    return openSocket;
  }, [applySignals]);

  useEffect(() => {
    isUnmountedRef.current = false;

    const start = async () => {
      try {
        await loadLatestSignals();
      } catch (error) {
        console.error("Initial signal fetch failed:", error);
        if (!signalsRef.current.length) {
          setStreamError("Signal stream temporarily unavailable.");
        }
      }

      const openSocket = connectSocket();
      openSocket();
    };

    start();

    return () => {
      isUnmountedRef.current = true;

      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (heartbeatTimerRef.current) {
        window.clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
      if (heartbeatTimeoutRef.current) {
        window.clearTimeout(heartbeatTimeoutRef.current);
        heartbeatTimeoutRef.current = null;
      }
      if (connectTimeoutRef.current) {
        window.clearTimeout(connectTimeoutRef.current);
        connectTimeoutRef.current = null;
      }

      const socket = socketRef.current;
      if (socket && socket.readyState < WebSocket.CLOSING) {
        socket.close();
      }
      socketRef.current = null;
    };
  }, [connectSocket, loadLatestSignals]);

  return {
    signals,
    streamError,
  };
}
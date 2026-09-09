"use client";

import { useSyncExternalStore } from "react";
import { getAuthToken } from "@/lib/api";

/**
 * Auth is optional. When the backend runs AUTH_REQUIRED=false everything works
 * token-less; when it's on, a session token from POST /api/auth/login is kept
 * in localStorage (see lib/api.ts). This hook reflects whether we currently
 * hold a token, updating on the custom `legalai:auth` event that setAuthToken
 * dispatches.
 */
function subscribe(cb: () => void) {
  window.addEventListener("legalai:auth", cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener("legalai:auth", cb);
    window.removeEventListener("storage", cb);
  };
}

export function useAuthToken(): string | null {
  return useSyncExternalStore(
    subscribe,
    () => getAuthToken(),
    () => null,
  );
}

const SESSION_KEY = "legalai.auth.session";

export interface SessionInfo {
  orgName: string;
  role: string;
  expiresAt: string;
  email: string;
}

export function saveSession(info: SessionInfo) {
  try {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(info));
    window.dispatchEvent(new Event("legalai:auth"));
  } catch {
    /* ignore */
  }
}

export function clearSession() {
  try {
    window.localStorage.removeItem(SESSION_KEY);
    window.dispatchEvent(new Event("legalai:auth"));
  } catch {
    /* ignore */
  }
}

export function useSession(): SessionInfo | null {
  const raw = useSyncExternalStore(
    subscribe,
    () => {
      try {
        return window.localStorage.getItem(SESSION_KEY);
      } catch {
        return null;
      }
    },
    () => null,
  );
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionInfo;
  } catch {
    return null;
  }
}

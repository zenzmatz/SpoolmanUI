import type { AuthProvider } from "@refinedev/core";
import { getAPIURL } from "./utils/url";

interface AuthStatusResponse {
  enabled: boolean;
  cookie_secure: boolean;
}

interface AuthIdentity {
  id: number;
  username: string;
  is_admin: boolean;
  created: string;
  last_login?: string;
}

function buildError(message: string, statusCode?: number): Error & { statusCode?: number } {
  const error = new Error(message) as Error & { statusCode?: number };
  error.statusCode = statusCode;
  return error;
}

async function getAuthStatus(): Promise<AuthStatusResponse> {
  const response = await fetch(`${getAPIURL()}/auth/status`, {
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw buildError("Failed to fetch auth status.", response.status);
  }

  return response.json();
}

async function getCurrentUser(): Promise<AuthIdentity | null> {
  const response = await fetch(`${getAPIURL()}/auth/me`, {
    credentials: "include",
    cache: "no-store",
  });

  if (response.status === 401 || response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw buildError("Failed to fetch current user.", response.status);
  }

  return response.json();
}

function isLikelySecureCookieHttpMismatch(status: AuthStatusResponse): boolean {
  return (
    status.cookie_secure &&
    globalThis.location?.protocol === "http:" &&
    !["localhost", "127.0.0.1", "[::1]"].includes(globalThis.location.hostname)
  );
}

function buildSessionNotPersistedMessage(status: AuthStatusResponse): string {
  if (isLikelySecureCookieHttpMismatch(status)) {
    return "Login succeeded, but the browser did not keep the secure session cookie. Use HTTPS or set SPOOLMAN_AUTH_COOKIE_SECURE=FALSE while testing over HTTP.";
  }

  return "Login succeeded, but the session cookie was not accepted by the browser.";
}

const authProvider: AuthProvider = {
  login: async (params) => {
    const response = await fetch(`${getAPIURL()}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        username: params?.username,
        password: params?.password,
      }),
    });

    if (!response.ok) {
      let message = "Login failed.";
      try {
        const payload = await response.json();
        if (typeof payload?.message === "string") {
          message = payload.message;
        }
      } catch {
        // Ignore parse failures and fall back to the generic message.
      }

      return {
        success: false,
        error: buildError(message, response.status),
      };
    }

    const currentUser = await getCurrentUser();
    if (!currentUser) {
      const status = await getAuthStatus();
      return {
        success: false,
        error: buildError(buildSessionNotPersistedMessage(status), 401),
      };
    }

    return {
      success: true,
      redirectTo: typeof params?.to === "string" && params.to !== "" ? params.to : "/",
    };
  },

  logout: async () => {
    try {
      await fetch(`${getAPIURL()}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Ignore logout transport errors so the UI can still reset locally.
    }

    return {
      success: true,
      redirectTo: "/login",
    };
  },

  check: async () => {
    const status = await getAuthStatus();
    if (!status.enabled) {
      return {
        authenticated: true,
      };
    }

    const currentUser = await getCurrentUser();
    if (currentUser) {
      return {
        authenticated: true,
      };
    }

    return {
      authenticated: false,
      redirectTo: "/login",
      logout: true,
    };
  },

  onError: async (error) => {
    const statusCode = error?.statusCode ?? error?.response?.status;
    if (statusCode === 401) {
      return {
        logout: true,
        redirectTo: "/login",
        error,
      };
    }

    return {};
  },

  getIdentity: async () => {
    const status = await getAuthStatus();
    if (!status.enabled) {
      return null;
    }

    return getCurrentUser();
  },
};

export default authProvider;

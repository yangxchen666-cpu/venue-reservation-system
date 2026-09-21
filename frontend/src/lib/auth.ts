const TOKEN_KEY = "token";

interface TokenPayload {
  sub: string;
  role: string;
  exp: number;
}

/** 解析 JWT payload；token 格式非法或已过期返回 null */
function parseToken(token: string): TokenPayload | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1])) as TokenPayload;
    if (typeof payload.exp !== "number" || payload.exp * 1000 <= Date.now()) return null;
    return payload;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/** token 存在且未过期视为已登录 */
export function isLoggedIn(): boolean {
  const token = getToken();
  return token !== null && parseToken(token) !== null;
}

/** 从 JWT payload 读取角色（避免为导航栏多请求一次 /auth/me）；未登录或 token 无效返回 null */
export function getUserRole(): string | null {
  const token = getToken();
  if (!token) return null;
  return parseToken(token)?.role ?? null;
}

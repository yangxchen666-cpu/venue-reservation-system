"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import { setToken } from "@/lib/auth";
import type { TokenResponse } from "@/lib/types";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await apiFetch<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(res.access_token);
      router.push(searchParams.get("next") ?? "/venues");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登录失败，请稍后重试");
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-xl border border-black/[.08] p-6 dark:border-white/[.145]">
      {searchParams.get("registered") === "1" && (
        <p className="mb-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
          注册成功，请登录
        </p>
      )}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm">
          用户名
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
            className="rounded-lg border border-black/[.08] px-3 py-2 outline-none focus:border-black dark:border-white/[.145] dark:focus:border-white"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          密码
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            className="rounded-lg border border-black/[.08] px-3 py-2 outline-none focus:border-black dark:border-white/[.145] dark:focus:border-white"
          />
        </label>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-full bg-black py-2 text-sm font-medium text-white transition-colors hover:bg-black/80 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/80"
        >
          {submitting ? "登录中…" : "登录"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-black/60 dark:text-white/70">
        没有账号？{" "}
        <Link href="/register" className="font-medium hover:underline">
          去注册
        </Link>
      </p>
    </div>
  );
}

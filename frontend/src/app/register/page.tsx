"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 客户端校验，规则与后端 schemas/auth.py 一致
  function validate(): string | null {
    if (!/^[A-Za-z0-9_]{3,32}$/.test(username)) {
      return "用户名须为 3-32 位字母、数字或下划线";
    }
    if (password.length < 6 || !/\p{L}/u.test(password) || !/\d/.test(password)) {
      return "密码长度至少 6 位，且需同时包含字母和数字";
    }
    if (password !== confirm) {
      return "两次输入的密码不一致";
    }
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const invalid = validate();
    if (invalid) {
      setError(invalid);
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      router.push("/login?registered=1");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "注册失败，请稍后重试");
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm pt-12">
      <h1 className="mb-6 text-center text-2xl font-semibold">注册</h1>
      <div className="rounded-xl border border-black/[.08] p-6 dark:border-white/[.145]">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-sm">
            用户名
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              placeholder="3-32 位字母、数字或下划线"
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
              autoComplete="new-password"
              placeholder="至少 6 位，含字母和数字"
              className="rounded-lg border border-black/[.08] px-3 py-2 outline-none focus:border-black dark:border-white/[.145] dark:focus:border-white"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-sm">
            确认密码
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              autoComplete="new-password"
              className="rounded-lg border border-black/[.08] px-3 py-2 outline-none focus:border-black dark:border-white/[.145] dark:focus:border-white"
            />
          </label>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="rounded-full bg-black py-2 text-sm font-medium text-white transition-colors hover:bg-black/80 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/80"
          >
            {submitting ? "注册中…" : "注册"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-black/60 dark:text-white/70">
          已有账号？{" "}
          <Link href="/login" className="font-medium hover:underline">
            去登录
          </Link>
        </p>
      </div>
    </div>
  );
}

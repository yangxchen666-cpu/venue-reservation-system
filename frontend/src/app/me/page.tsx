"use client";

import { useEffect, useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import type { MeResponse, Role } from "@/lib/types";

const ROLE_LABELS: Record<Role, { label: string; className: string }> = {
  user: {
    label: "普通用户",
    className: "bg-black/[.03] text-black/60 dark:bg-white/[.05] dark:text-white/70",
  },
  venue_admin: {
    label: "场地管理员",
    className: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400",
  },
  admin: {
    label: "系统管理员",
    className: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  },
};

export default function MePage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const data = await apiFetch<MeResponse>("/auth/me", { signal: controller.signal });
        setMe(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
      }
    })();
    return () => controller.abort();
  }, [refreshKey]);

  async function handleApply() {
    if (!window.confirm("确认申请成为场地管理员吗？")) return;
    setSubmitting(true);
    setError("");
    setNotice("");
    try {
      await apiFetch("/auth/apply-venue-admin", { method: "POST" });
      setNotice("申请已提交，等待管理员审批");
      setRefreshKey((k) => k + 1); // 重新拉取 me，申请区变为「审批中」
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "申请失败，请稍后重试");
      setRefreshKey((k) => k + 1); // 409（已有待审批申请等）后同步最新状态
    } finally {
      setSubmitting(false);
    }
  }

  const role = me ? ROLE_LABELS[me.role] : null;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-semibold">个人中心</h1>

      {error && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
          {error}
        </p>
      )}
      {notice && (
        <p className="mb-4 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
          {notice}
        </p>
      )}

      {!me && !error && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>
      )}

      {me && (
        <>
          <div className="rounded-xl border border-black/[.08] p-5 dark:border-white/[.145]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{me.username}</h2>
                <p className="mt-1 text-sm text-black/60 dark:text-white/70">
                  注册于 {me.created_at.slice(0, 10)}
                </p>
              </div>
              {role && (
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs ${role.className}`}>
                  {role.label}
                </span>
              )}
            </div>
          </div>

          {me.role === "user" && (
            <div className="mt-4 rounded-xl border border-black/[.08] p-5 dark:border-white/[.145]">
              <h3 className="text-base font-semibold">场地管理员申请</h3>
              {me.application_status === "pending" && (
                <p className="mt-3 text-sm text-black/60 dark:text-white/70">
                  申请审批中，请耐心等待管理员处理。
                </p>
              )}
              {me.application_status === "rejected" && (
                <>
                  <p className="mt-3 text-sm text-amber-700 dark:text-amber-400">
                    上次申请已被驳回，可重新申请。
                  </p>
                  <button
                    onClick={handleApply}
                    disabled={submitting}
                    className="mt-4 cursor-pointer rounded-full bg-black px-4 py-1.5 text-sm text-white transition-colors hover:bg-black/80 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/80"
                  >
                    {submitting ? "提交中…" : "重新申请"}
                  </button>
                </>
              )}
              {me.application_status === "approved" && (
                <p className="mt-3 text-sm text-emerald-700 dark:text-emerald-400">
                  申请已通过，你已成为场地管理员。
                </p>
              )}
              {me.application_status === null && (
                <>
                  <p className="mt-3 text-sm text-black/60 dark:text-white/70">
                    申请通过后可创建并管理自己的球场。
                  </p>
                  <button
                    onClick={handleApply}
                    disabled={submitting}
                    className="mt-4 cursor-pointer rounded-full bg-black px-4 py-1.5 text-sm text-white transition-colors hover:bg-black/80 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/80"
                  >
                    {submitting ? "提交中…" : "申请成为场地管理员"}
                  </button>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

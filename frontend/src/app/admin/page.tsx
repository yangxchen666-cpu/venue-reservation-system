"use client";

import { useEffect, useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import {
  COURT_TYPES,
  type AdminApplication,
  type AdminBooking,
  type ApplicationStatus,
  type BookingStatus,
  type Court,
  type MeResponse,
  type Role,
  type User,
} from "@/lib/types";

const SLOT_MINUTES_OPTIONS = [60, 120, 180];

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

function formatPrice(price: string | number | null): string {
  if (price === null) return "—";
  return `¥${Number(price).toFixed(2)}`;
}

/** "HH:MM:SS" → "HH:MM" */
function formatTime(t: string): string {
  return t.slice(0, 5);
}

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "user", label: "普通用户" },
  { value: "venue_admin", label: "场地管理员" },
  { value: "admin", label: "系统管理员" },
];

const APP_STATUS_BADGE: Record<ApplicationStatus, { label: string; className: string }> = {
  pending: {
    label: "待审批",
    className: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
  },
  approved: {
    label: "已通过",
    className: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  },
  rejected: {
    label: "已驳回",
    className: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400",
  },
};

type DisplayStatus = BookingStatus | "expired";

const STATUS_BADGE: Record<DisplayStatus, { label: string; className: string }> = {
  booked: {
    label: "已预定",
    className: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  },
  checked_in: {
    label: "已核销",
    className: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400",
  },
  cancelled: {
    label: "已取消",
    className: "bg-black/[.03] text-black/40 dark:bg-white/[.05] dark:text-white/40",
  },
  expired: {
    label: "已过期",
    className: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
  },
};

/** Q-05：过期未核销由前端推导展示「已过期」，不新增后端状态 */
function displayStatus(b: AdminBooking, now: Date): DisplayStatus {
  if (b.status !== "booked") return b.status;
  return new Date(`${b.date}T${b.start_time}`) <= now ? "expired" : "booked";
}

const inputCls =
  "rounded-lg border border-black/[.08] px-3 py-2 outline-none focus:border-black dark:border-white/[.145] dark:bg-[#0a0a0a] dark:focus:border-white";

function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
      {message}
    </p>
  );
}

function Loading() {
  return <p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>;
}

/* ---------- Tab 1：用户管理 ---------- */

function UsersTab() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const [meData, usersData] = await Promise.all([
          apiFetch<MeResponse>("/auth/me", { signal: controller.signal }),
          apiFetch<User[]>("/admin/users", { signal: controller.signal }),
        ]);
        setMe(meData);
        setUsers(usersData);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        setUsers([]);
      }
    })();
    return () => controller.abort();
  }, [refreshKey]);

  async function handleRoleChange(user: User, role: Role) {
    if (role === user.role) return;
    const label = ROLE_OPTIONS.find((o) => o.value === role)?.label ?? role;
    if (!window.confirm(`确认将「${user.username}」的角色改为「${label}」吗？`)) return;
    setError("");
    try {
      const updated = await apiFetch<User>(`/admin/users/${user.id}/role`, {
        method: "PUT",
        body: JSON.stringify({ role }),
      });
      setUsers((prev) => prev?.map((u) => (u.id === updated.id ? updated : u)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "修改失败，请稍后重试");
      setRefreshKey((k) => k + 1); // 409（改自己）/失败后还原下拉显示
    }
  }

  return (
    <div>
      <ErrorBanner message={error} />
      {users === null && !error && <Loading />}
      {users !== null && (
        <ul className="space-y-3">
          {users.map((user) => (
            <li
              key={user.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-black/[.08] p-5 dark:border-white/[.145]"
            >
              <div>
                <h2 className="text-base font-semibold">
                  {user.username}
                  {me?.id === user.id && (
                    <span className="ml-2 text-xs font-normal text-black/40 dark:text-white/40">（我）</span>
                  )}
                </h2>
                <p className="mt-1 text-sm text-black/60 dark:text-white/70">
                  #{user.id} · 注册于 {user.created_at.slice(0, 10)}
                </p>
              </div>
              <select
                value={user.role}
                disabled={me?.id === user.id} // SPEC-D2：不能修改自己的角色
                onChange={(e) => handleRoleChange(user, e.target.value as Role)}
                className="cursor-pointer rounded-lg border border-black/[.08] px-3 py-1.5 text-sm outline-none focus:border-black disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/[.145] dark:bg-[#0a0a0a] dark:focus:border-white"
              >
                {ROLE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ---------- Tab 2：申请审批 ---------- */

function ApplicationsTab() {
  const [statusFilter, setStatusFilter] = useState<"" | ApplicationStatus>("pending");
  const [applications, setApplications] = useState<AdminApplication[] | null>(null);
  const [error, setError] = useState("");
  const [actingId, setActingId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const qs = statusFilter ? `?status=${statusFilter}` : "";
        const data = await apiFetch<AdminApplication[]>(`/admin/applications${qs}`, {
          signal: controller.signal,
        });
        setApplications(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        setApplications([]);
      }
    })();
    return () => controller.abort();
  }, [statusFilter, refreshKey]);

  async function handleReview(app: AdminApplication, approve: boolean) {
    const action = approve ? "批准" : "驳回";
    if (!window.confirm(`确认${action}「${app.username}」的场地管理员申请吗？`)) return;
    setActingId(app.id);
    setError("");
    try {
      await apiFetch(`/admin/applications/${app.id}/${approve ? "approve" : "reject"}`, {
        method: "POST",
      });
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败，请稍后重试");
      setRefreshKey((k) => k + 1);
    } finally {
      setActingId(null);
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-3 text-sm">
        <label className="flex items-center gap-2">
          状态
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as "" | ApplicationStatus)}
            className={inputCls}
          >
            <option value="pending">待审批</option>
            <option value="approved">已通过</option>
            <option value="rejected">已驳回</option>
            <option value="">全部</option>
          </select>
        </label>
      </div>

      <ErrorBanner message={error} />
      {applications === null && !error && <Loading />}
      {applications !== null && applications.length === 0 && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">暂无申请</p>
      )}
      {applications !== null && applications.length > 0 && (
        <ul className="space-y-3">
          {applications.map((app) => {
            const badge = APP_STATUS_BADGE[app.status];
            return (
              <li
                key={app.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-black/[.08] p-5 dark:border-white/[.145]"
              >
                <div>
                  <h2 className="text-base font-semibold">{app.username}</h2>
                  <p className="mt-1 text-sm text-black/60 dark:text-white/70">
                    申请于 {app.created_at.slice(0, 10)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs ${badge.className}`}>
                    {badge.label}
                  </span>
                  {app.status === "pending" && (
                    <>
                      <button
                        onClick={() => handleReview(app, true)}
                        disabled={actingId !== null}
                        className="cursor-pointer rounded-full bg-black px-4 py-1.5 text-sm text-white transition-colors hover:bg-black/80 disabled:opacity-40 dark:bg-white dark:text-black dark:hover:bg-white/80"
                      >
                        批准
                      </button>
                      <button
                        onClick={() => handleReview(app, false)}
                        disabled={actingId !== null}
                        className="cursor-pointer rounded-full border border-black/[.08] px-4 py-1.5 text-sm transition-colors hover:border-black disabled:opacity-40 dark:border-white/[.145] dark:hover:border-white"
                      >
                        驳回
                      </button>
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/* ---------- Tab 3：球场管理 ---------- */

interface CourtForm {
  name: string;
  type: string;
  price: string;
  open_time: string; // "HH:MM"
  close_time: string; // "HH:MM"
  slot_minutes: number;
}

function toCourtForm(court: Court): CourtForm {
  return {
    name: court.name,
    type: court.type,
    price: String(court.price),
    open_time: court.open_time.slice(0, 5),
    close_time: court.close_time.slice(0, 5),
    slot_minutes: court.slot_minutes,
  };
}

function CourtsTab() {
  const [courts, setCourts] = useState<Court[] | null>(null);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [editing, setEditing] = useState<Court | null>(null);
  const [form, setForm] = useState<CourtForm | null>(null);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const data = await apiFetch<Court[]>("/admin/courts", { signal: controller.signal });
        setCourts(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        setCourts([]);
      }
    })();
    return () => controller.abort();
  }, [refreshKey]);

  function openEdit(court: Court) {
    setEditing(court);
    setForm(toCourtForm(court));
    setFormError("");
  }

  async function handleSubmit() {
    if (!editing || !form) return;
    setSubmitting(true);
    setFormError("");
    try {
      await apiFetch(`/admin/courts/${editing.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: form.name,
          type: form.type,
          price: Number(form.price),
          open_time: `${form.open_time}:00`,
          close_time: `${form.close_time}:00`,
          slot_minutes: form.slot_minutes,
        }),
      });
      setEditing(null);
      setForm(null);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "保存失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(court: Court) {
    if (!window.confirm(`确认删除球场「${court.name}」吗？此操作不可恢复。`)) return;
    setError("");
    try {
      await apiFetch(`/admin/courts/${court.id}`, { method: "DELETE" });
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除失败，请稍后重试");
    }
  }

  return (
    <div>
      <ErrorBanner message={error} />
      {courts === null && !error && <Loading />}
      {courts !== null && !error && courts.length === 0 && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">暂无球场</p>
      )}
      {courts !== null && courts.length > 0 && (
        <ul className="space-y-3">
          {courts.map((court) => (
            <li
              key={court.id}
              className="rounded-xl border border-black/[.08] p-5 dark:border-white/[.145]"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold">{court.name}</h2>
                  <p className="mt-1 text-sm text-black/60 dark:text-white/70">
                    {court.type} · 开放时间 {formatTime(court.open_time)} - {formatTime(court.close_time)} · 每{" "}
                    {court.slot_minutes} 分钟一节
                  </p>
                  <p className="mt-1 text-lg font-medium">{formatPrice(court.price)}</p>
                </div>
                <div className="flex shrink-0 gap-3">
                  <button
                    onClick={() => openEdit(court)}
                    className="cursor-pointer rounded-full border border-black/[.08] px-4 py-1.5 text-sm transition-colors hover:border-black dark:border-white/[.145] dark:hover:border-white"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(court)}
                    className="cursor-pointer rounded-full border border-red-200 px-4 py-1.5 text-sm text-red-600 transition-colors hover:border-red-400 dark:border-red-900 dark:text-red-400 dark:hover:border-red-700"
                  >
                    删除
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {editing && form && (
        <div
          className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 p-4"
          onClick={() => !submitting && setEditing(null)}
        >
          <div
            className="w-full max-w-md rounded-xl bg-white p-6 dark:bg-[#0a0a0a]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-4 text-base font-semibold">编辑球场</h3>
            {formError && (
              <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
                {formError}
              </p>
            )}
            <div className="space-y-4 text-sm">
              <label className="flex flex-col gap-1.5">
                名称
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  maxLength={50}
                  className={inputCls}
                />
              </label>
              <div className="grid grid-cols-2 gap-4">
                <label className="flex flex-col gap-1.5">
                  类型
                  <select
                    value={form.type}
                    onChange={(e) => setForm({ ...form, type: e.target.value })}
                    className={inputCls}
                  >
                    {COURT_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1.5">
                  价格
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.price}
                    onChange={(e) => setForm({ ...form, price: e.target.value })}
                    className={inputCls}
                  />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <label className="flex flex-col gap-1.5">
                  开放时间
                  <input
                    type="time"
                    value={form.open_time}
                    onChange={(e) => setForm({ ...form, open_time: e.target.value })}
                    className={inputCls}
                  />
                </label>
                <label className="flex flex-col gap-1.5">
                  关闭时间
                  <input
                    type="time"
                    value={form.close_time}
                    onChange={(e) => setForm({ ...form, close_time: e.target.value })}
                    className={inputCls}
                  />
                </label>
              </div>
              <label className="flex flex-col gap-1.5">
                时段粒度
                <select
                  value={form.slot_minutes}
                  onChange={(e) => setForm({ ...form, slot_minutes: Number(e.target.value) })}
                  className={inputCls}
                >
                  {SLOT_MINUTES_OPTIONS.map((m) => (
                    <option key={m} value={m}>
                      {m} 分钟
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => setEditing(null)}
                disabled={submitting}
                className="flex-1 cursor-pointer rounded-full border border-black/[.08] py-2 text-sm transition-colors hover:border-black disabled:opacity-50 dark:border-white/[.145] dark:hover:border-white"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 cursor-pointer rounded-full bg-black py-2 text-sm font-medium text-white transition-colors hover:bg-black/80 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/80"
              >
                {submitting ? "保存中…" : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Tab 4：预定管理 ---------- */

function BookingsTab() {
  const [bookings, setBookings] = useState<AdminBooking[] | null>(null);
  const [error, setError] = useState("");
  const [actingId, setActingId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const data = await apiFetch<AdminBooking[]>("/admin/bookings", { signal: controller.signal });
        setBookings(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        setBookings([]);
      }
    })();
    return () => controller.abort();
  }, [refreshKey]);

  async function handleCancel(b: AdminBooking) {
    if (!window.confirm(`确认取消「${b.username}」${b.date} ${b.start_time.slice(0, 5)} 的预定吗？`))
      return;
    setActingId(b.id);
    setError("");
    try {
      await apiFetch(`/admin/bookings/${b.id}`, { method: "DELETE" });
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "取消失败，请稍后重试");
      setRefreshKey((k) => k + 1);
    } finally {
      setActingId(null);
    }
  }

  const now = new Date();

  return (
    <div>
      <ErrorBanner message={error} />
      {bookings === null && !error && <Loading />}
      {bookings !== null && !error && bookings.length === 0 && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">暂无预定</p>
      )}
      {bookings !== null && bookings.length > 0 && (
        <ul className="space-y-3">
          {bookings.map((b) => {
            const status = displayStatus(b, now);
            const badge = STATUS_BADGE[status];
            const started = new Date(`${b.date}T${b.start_time}`) <= now;
            return (
              <li
                key={b.id}
                className="rounded-xl border border-black/[.08] p-5 dark:border-white/[.145]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-base font-semibold">
                      {b.username} · {b.court_name}
                    </h2>
                    <p className="mt-1 text-sm text-black/60 dark:text-white/70">
                      {b.date} {WEEKDAYS[new Date(`${b.date}T00:00:00`).getDay()]} ·{" "}
                      {b.start_time.slice(0, 5)} 开始 · {formatPrice(b.price)}
                    </p>
                  </div>
                  <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs ${badge.className}`}>
                    {badge.label}
                  </span>
                </div>
                <div className="mt-3 flex justify-end">
                  <button
                    onClick={() => handleCancel(b)}
                    disabled={b.status !== "booked" || started || actingId !== null}
                    className="cursor-pointer rounded-full border border-black/[.08] px-4 py-1.5 text-sm transition-colors hover:border-black disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/[.145] dark:hover:border-white"
                  >
                    取消预定
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/* ---------- 页面 ---------- */

export default function AdminPage() {
  const [tab, setTab] = useState<"users" | "applications" | "courts" | "bookings">("users");

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">系统管理员后台</h1>
      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-black/[.08] dark:border-white/[.145]">
        {(
          [
            ["users", "用户管理"],
            ["applications", "申请审批"],
            ["courts", "球场管理"],
            ["bookings", "预定管理"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`shrink-0 cursor-pointer px-4 py-2 text-sm transition-colors ${
              tab === key
                ? "border-b-2 border-black font-medium dark:border-white"
                : "text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "users" && <UsersTab />}
      {tab === "applications" && <ApplicationsTab />}
      {tab === "courts" && <CourtsTab />}
      {tab === "bookings" && <BookingsTab />}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import { COURT_TYPES, type AdminBooking, type BookingStatus, type Court } from "@/lib/types";

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

/* ---------- Tab 1：我的球场 ---------- */

interface CourtForm {
  name: string;
  type: string;
  price: string;
  open_time: string; // "HH:MM"
  close_time: string; // "HH:MM"
  slot_minutes: number;
}

const EMPTY_FORM: CourtForm = {
  name: "",
  type: COURT_TYPES[0],
  price: "",
  open_time: "08:00",
  close_time: "22:00",
  slot_minutes: 60,
};

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
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Court | null>(null);
  const [form, setForm] = useState<CourtForm>(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const data = await apiFetch<Court[]>("/venue-admin/courts", { signal: controller.signal });
        setCourts(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        setCourts([]);
      }
    })();
    return () => controller.abort();
  }, [refreshKey]);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError("");
    setFormOpen(true);
  }

  function openEdit(court: Court) {
    setEditing(court);
    setForm(toCourtForm(court));
    setFormError("");
    setFormOpen(true);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError("");
    try {
      const body = {
        name: form.name,
        type: form.type,
        price: Number(form.price),
        open_time: `${form.open_time}:00`,
        close_time: `${form.close_time}:00`,
        slot_minutes: form.slot_minutes,
      };
      if (editing) {
        await apiFetch(`/venue-admin/courts/${editing.id}`, {
          method: "PUT",
          body: JSON.stringify(body),
        });
      } else {
        await apiFetch("/venue-admin/courts", { method: "POST", body: JSON.stringify(body) });
      }
      setFormOpen(false);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "保存失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <button
          onClick={openCreate}
          className="cursor-pointer rounded-full bg-black px-4 py-1.5 text-sm text-white transition-colors hover:bg-black/80 dark:bg-white dark:text-black dark:hover:bg-white/80"
        >
          + 新建球场
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
          {error}
        </p>
      )}

      {courts === null && !error && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>
      )}
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
                <button
                  onClick={() => openEdit(court)}
                  className="shrink-0 cursor-pointer rounded-full border border-black/[.08] px-4 py-1.5 text-sm transition-colors hover:border-black dark:border-white/[.145] dark:hover:border-white"
                >
                  编辑
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {formOpen && (
        <div
          className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 p-4"
          onClick={() => !submitting && setFormOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-xl bg-white p-6 dark:bg-[#0a0a0a]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-4 text-base font-semibold">{editing ? "编辑球场" : "新建球场"}</h3>
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
                onClick={() => setFormOpen(false)}
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

/* ---------- Tab 2：预定管理 ---------- */

function toDateStr(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

/** 月历格子：null 为月初前置空白 */
function buildMonthGrid(year: number, month: number): (number | null)[] {
  const first = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < first.getDay(); i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  return cells;
}

function BookingsTab() {
  const [view, setView] = useState<"month" | "day">("month");
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });
  const [calendar, setCalendar] = useState<AdminBooking[] | null>(null);
  const [selectedDate, setSelectedDate] = useState(() => toDateStr(new Date()));
  const [bookings, setBookings] = useState<AdminBooking[] | null>(null);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [actingId, setActingId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // 月视图数据（Q-17：日历接口按月返回）
  useEffect(() => {
    if (view !== "month") return;
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const mm = `${month.year}-${String(month.month).padStart(2, "0")}`;
        const data = await apiFetch<AdminBooking[]>(`/venue-admin/bookings/calendar?month=${mm}`, {
          signal: controller.signal,
        });
        setCalendar(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        setCalendar([]);
      }
    })();
    return () => controller.abort();
  }, [view, month, refreshKey]);

  // 日视图数据：按日期筛选的列表
  useEffect(() => {
    if (view !== "day") return;
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const data = await apiFetch<AdminBooking[]>(`/venue-admin/bookings?date=${selectedDate}`, {
          signal: controller.signal,
        });
        setBookings(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        setBookings([]);
      }
    })();
    return () => controller.abort();
  }, [view, selectedDate, refreshKey]);

  function shiftMonth(delta: number) {
    setMonth((m) => {
      const d = new Date(m.year, m.month - 1 + delta, 1);
      return { year: d.getFullYear(), month: d.getMonth() + 1 };
    });
  }

  async function handleCheckIn(b: AdminBooking) {
    if (
      !window.confirm(
        `确认核销「${b.username}」${b.date} ${b.start_time.slice(0, 5)} 在「${b.court_name}」的预定吗？`,
      )
    )
      return;
    setActingId(b.id);
    setActionError("");
    try {
      await apiFetch(`/venue-admin/bookings/${b.id}/check-in`, { method: "POST" });
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "核销失败，请稍后重试");
      setRefreshKey((k) => k + 1);
    } finally {
      setActingId(null);
    }
  }

  async function handleCancel(b: AdminBooking) {
    if (!window.confirm(`确认取消「${b.username}」${b.date} ${b.start_time.slice(0, 5)} 的预定吗？`))
      return;
    setActingId(b.id);
    setActionError("");
    try {
      await apiFetch(`/venue-admin/bookings/${b.id}`, { method: "DELETE" });
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "取消失败，请稍后重试");
      setRefreshKey((k) => k + 1);
    } finally {
      setActingId(null);
    }
  }

  const counts = new Map<string, number>();
  (calendar ?? []).forEach((b) => counts.set(b.date, (counts.get(b.date) ?? 0) + 1));
  const now = new Date();

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex overflow-hidden rounded-full border border-black/[.08] text-sm dark:border-white/[.145]">
          {(["month", "day"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`cursor-pointer px-4 py-1.5 transition-colors ${
                view === v
                  ? "bg-black text-white dark:bg-white dark:text-black"
                  : "hover:bg-black/[.03] dark:hover:bg-white/[.05]"
              }`}
            >
              {v === "month" ? "月视图" : "日视图"}
            </button>
          ))}
        </div>
        {view === "day" && (
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className={inputCls}
          />
        )}
        {view === "month" && (
          <div className="flex items-center gap-2 text-sm">
            <button
              onClick={() => shiftMonth(-1)}
              className="cursor-pointer rounded-full border border-black/[.08] px-3 py-1.5 transition-colors hover:border-black dark:border-white/[.145] dark:hover:border-white"
            >
              ←
            </button>
            <span className="min-w-24 text-center font-medium">
              {month.year} 年 {month.month} 月
            </span>
            <button
              onClick={() => shiftMonth(1)}
              className="cursor-pointer rounded-full border border-black/[.08] px-3 py-1.5 transition-colors hover:border-black dark:border-white/[.145] dark:hover:border-white"
            >
              →
            </button>
          </div>
        )}
      </div>

      {error && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
          {error}
        </p>
      )}
      {actionError && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
          {actionError}
        </p>
      )}

      {view === "month" &&
        (calendar === null && !error ? (
          <p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>
        ) : (
          <div className="grid grid-cols-7 gap-1">
            {WEEKDAYS.map((w) => (
              <div key={w} className="py-1 text-center text-xs text-black/40 dark:text-white/40">
                {w}
              </div>
            ))}
            {buildMonthGrid(month.year, month.month).map((day, i) => {
              if (day === null) return <div key={`blank-${i}`} />;
              const dateStr = `${month.year}-${String(month.month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
              const count = counts.get(dateStr) ?? 0;
              return (
                <button
                  key={dateStr}
                  onClick={() => {
                    setSelectedDate(dateStr);
                    setView("day");
                  }}
                  className="aspect-square cursor-pointer rounded-lg border border-black/[.08] p-2 text-left text-sm transition-colors hover:border-black dark:border-white/[.145] dark:hover:border-white"
                >
                  <span className="block">{day}</span>
                  <span
                    className={`mt-0.5 block text-xs ${
                      count > 0
                        ? "font-medium text-emerald-700 dark:text-emerald-400"
                        : "text-black/25 dark:text-white/25"
                    }`}
                  >
                    {count > 0 ? `${count} 单` : "—"}
                  </span>
                </button>
              );
            })}
          </div>
        ))}

      {view === "day" &&
        (bookings === null && !error ? (
          <p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>
        ) : bookings && bookings.length === 0 ? (
          <p className="py-16 text-center text-black/60 dark:text-white/70">当天暂无预定</p>
        ) : (
          <ul className="space-y-3">
            {(bookings ?? []).map((b) => {
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
                        {b.court_name} · {b.username}
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
                  <div className="mt-3 flex justify-end gap-3">
                    <button
                      onClick={() => handleCheckIn(b)}
                      disabled={b.status !== "booked" || actingId !== null}
                      className="cursor-pointer rounded-full border border-black/[.08] px-4 py-1.5 text-sm transition-colors hover:border-black disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/[.145] dark:hover:border-white"
                    >
                      核销
                    </button>
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
        ))}
    </div>
  );
}

/* ---------- 页面 ---------- */

export default function VenueAdminPage() {
  const [tab, setTab] = useState<"courts" | "bookings">("courts");

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">场地管理员工作台</h1>
      <div className="mb-6 flex gap-1 border-b border-black/[.08] dark:border-white/[.145]">
        {(
          [
            ["courts", "我的球场"],
            ["bookings", "预定管理"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`cursor-pointer px-4 py-2 text-sm transition-colors ${
              tab === key
                ? "border-b-2 border-black font-medium dark:border-white"
                : "text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "courts" ? <CourtsTab /> : <BookingsTab />}
    </div>
  );
}

"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import type { Booking, BookingStatus } from "@/lib/types";

function formatPrice(price: string | number | null): string {
  if (price === null) return "—";
  return `¥${Number(price).toFixed(2)}`;
}

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

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

/** Q-05：过期未核销由前端按 date+start_time 与当前时间比较推导展示「已过期」，不新增后端状态 */
function displayStatus(b: Booking, now: Date): DisplayStatus {
  if (b.status !== "booked") return b.status;
  return new Date(`${b.date}T${b.start_time}`) <= now ? "expired" : "booked";
}

function OrdersContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [error, setError] = useState("");
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [showBookedHint, setShowBookedHint] = useState(searchParams.get("booked") === "1");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setError("");
      try {
        const data = await apiFetch<Booking[]>("/bookings/my", { signal: controller.signal });
        setBookings(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        setBookings([]);
      }
    })();
    return () => controller.abort();
  }, [refreshKey]);

  async function handleCancel(b: Booking) {
    const label = `${b.court_name ?? `球场 #${b.court_id}`} ${b.date} ${b.start_time.slice(0, 5)}`;
    if (!window.confirm(`确认取消「${label}」的预定吗？`)) return;
    setCancellingId(b.id);
    setError("");
    try {
      await apiFetch<Booking>(`/bookings/${b.id}`, { method: "DELETE" });
      setBookings((prev) =>
        prev ? prev.map((x) => (x.id === b.id ? { ...x, status: "cancelled" } : x)) : prev,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "取消失败，请稍后重试");
      setRefreshKey((k) => k + 1); // 409（时限/状态已变化）后重新拉取
    } finally {
      setCancellingId(null);
    }
  }

  const now = new Date();

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-baseline justify-between gap-2">
        <h1 className="text-2xl font-semibold">我的预定</h1>
        <Link
          href="/venues"
          className="text-sm text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white"
        >
          去预定 →
        </Link>
      </div>

      {showBookedHint && (
        <div className="mb-4 flex items-center justify-between rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
          预定成功
          <button
            onClick={() => {
              setShowBookedHint(false);
              router.replace("/orders");
            }}
            className="cursor-pointer opacity-70 transition-opacity hover:opacity-100"
          >
            关闭
          </button>
        </div>
      )}

      {error && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
          {error}
        </p>
      )}

      {bookings === null && !error && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>
      )}
      {bookings !== null && !error && bookings.length === 0 && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">暂无预定</p>
      )}
      {bookings !== null && bookings.length > 0 && (
        <ul className="space-y-3">
          {bookings.map((b) => {
            const status = displayStatus(b, now);
            const badge = STATUS_BADGE[status];
            const started = new Date(`${b.date}T${b.start_time}`) <= now;
            const cancellable = status === "booked" && !started;
            return (
              <li
                key={b.id}
                className="rounded-xl border border-black/[.08] p-5 dark:border-white/[.145]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-base font-semibold">
                      {b.court_name ?? `球场 #${b.court_id}`}
                    </h2>
                    <p className="mt-1 text-sm text-black/60 dark:text-white/70">
                      {b.date} {WEEKDAYS[new Date(`${b.date}T00:00:00`).getDay()]} ·{" "}
                      {b.start_time.slice(0, 5)} 开始
                    </p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-xs ${badge.className}`}
                  >
                    {badge.label}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <p className="text-lg font-medium">{formatPrice(b.price)}</p>
                  <button
                    onClick={() => handleCancel(b)}
                    disabled={!cancellable || cancellingId !== null}
                    className="cursor-pointer rounded-full border border-black/[.08] px-4 py-1.5 text-sm transition-colors hover:border-black disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/[.145] dark:hover:border-white"
                  >
                    {cancellingId === b.id ? "取消中…" : "取消预定"}
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

export default function OrdersPage() {
  return (
    <Suspense fallback={<p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>}>
      <OrdersContent />
    </Suspense>
  );
}

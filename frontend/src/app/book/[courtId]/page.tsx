"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";
import type { Booking, Court } from "@/lib/types";

function formatPrice(price: string | number): string {
  return `¥${Number(price).toFixed(2)}`;
}

function toDateStr(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

/** 由开放时间与时段粒度生成全部时段起点（SPEC 9.2） */
function buildSlots(openTime: string, closeTime: string, slotMinutes: number): string[] {
  const [oh, om] = openTime.split(":").map(Number);
  const [ch, cm] = closeTime.split(":").map(Number);
  const open = oh * 60 + om;
  const close = ch * 60 + cm;
  const slots: string[] = [];
  for (let t = open; t + slotMinutes <= close; t += slotMinutes) {
    slots.push(`${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`);
  }
  return slots;
}

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

export default function BookPage() {
  const { courtId } = useParams<{ courtId: string }>();
  const router = useRouter();
  // 可预约日期：今天起 7 天（Q-20 基线），默认今天
  const [dates] = useState<Date[]>(() => {
    const now = new Date();
    return Array.from(
      { length: 7 },
      (_, i) => new Date(now.getFullYear(), now.getMonth(), now.getDate() + i),
    );
  });
  const [selectedDate, setSelectedDate] = useState(() => toDateStr(new Date()));
  const [court, setCourt] = useState<Court | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [pageError, setPageError] = useState("");
  const [bookedSlots, setBookedSlots] = useState<Set<string>>(new Set());
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [bookError, setBookError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // 场地信息
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const data = await apiFetch<Court>(`/courts/${courtId}`, { signal: controller.signal });
        setCourt(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else {
          setPageError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
        }
      }
    })();
    return () => controller.abort();
  }, [courtId]);

  // 已订时段：初次加载 / 切换日期 / 下单 409 后刷新置灰
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const data = await apiFetch<string[]>(`/courts/${courtId}/booked-slots?date=${selectedDate}`, {
          signal: controller.signal,
        });
        setBookedSlots(new Set(data.map((t) => t.slice(0, 5))));
      } catch {
        // 已订时段加载失败不阻塞页面，下单时后端仍会兜底 409
      }
    })();
    return () => controller.abort();
  }, [courtId, selectedDate, refreshKey]);

  const slots = court ? buildSlots(court.open_time, court.close_time, court.slot_minutes) : [];
  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  const isToday = selectedDate === toDateStr(now);

  function isPast(slot: string): boolean {
    if (!isToday) return false;
    const [h, m] = slot.split(":").map(Number);
    return h * 60 + m <= nowMinutes;
  }

  function handleSlotClick(slot: string) {
    if (!isLoggedIn()) {
      router.push(`/login?next=/book/${courtId}`);
      return;
    }
    setBookError("");
    setSelectedSlot(slot);
  }

  async function handleConfirm() {
    if (!court || !selectedSlot) return;
    setSubmitting(true);
    try {
      await apiFetch<Booking>("/bookings", {
        method: "POST",
        body: JSON.stringify({
          court_id: court.id,
          date: selectedDate,
          start_time: `${selectedSlot}:00`,
        }),
      });
      router.push("/orders?booked=1");
    } catch (err) {
      setSelectedSlot(null);
      setBookError(err instanceof ApiError ? err.message : "预定失败，请稍后重试");
      setRefreshKey((k) => k + 1); // 409 抢占失败后刷新置灰
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        href={`/venues/${courtId}`}
        className="mb-6 inline-block text-sm text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white"
      >
        ← 返回场地详情
      </Link>
      {notFound && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">场地不存在</p>
      )}
      {!notFound && pageError && (
        <p className="py-16 text-center text-red-600 dark:text-red-400">{pageError}</p>
      )}
      {!notFound && !pageError && !court && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>
      )}
      {court && (
        <>
          <div className="mb-4 flex items-baseline justify-between gap-2">
            <h1 className="text-2xl font-semibold">{court.name}</h1>
            <span className="text-sm text-black/60 dark:text-white/70">
              {court.type} · {formatPrice(court.price)}/节
            </span>
          </div>

          <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
            {dates.map((d, i) => {
              const dateStr = toDateStr(d);
              const label =
                i === 0
                  ? `今天 ${WEEKDAYS[d.getDay()]}`
                  : i === 1
                    ? `明天 ${WEEKDAYS[d.getDay()]}`
                    : `${d.getMonth() + 1}/${d.getDate()} ${WEEKDAYS[d.getDay()]}`;
              const selected = dateStr === selectedDate;
              return (
                <button
                  key={dateStr}
                  onClick={() => {
                    setSelectedDate(dateStr);
                    setBookError("");
                  }}
                  className={`shrink-0 cursor-pointer rounded-full px-4 py-1.5 text-sm transition-colors ${
                    selected
                      ? "bg-black text-white dark:bg-white dark:text-black"
                      : "border border-black/[.08] hover:border-black dark:border-white/[.145] dark:hover:border-white"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {bookError && (
            <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
              {bookError}
            </p>
          )}

          <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
            {slots.map((slot) => {
              const booked = bookedSlots.has(slot);
              const past = isPast(slot);
              const disabled = booked || past;
              return (
                <button
                  key={slot}
                  disabled={disabled}
                  onClick={() => handleSlotClick(slot)}
                  className={`rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                    disabled
                      ? "cursor-not-allowed border-transparent bg-black/[.03] text-black/30 dark:bg-white/[.05] dark:text-white/30"
                      : "cursor-pointer border-black/[.08] hover:border-black dark:border-white/[.145] dark:hover:border-white"
                  }`}
                >
                  {slot}
                  <span className="mt-0.5 block text-xs">{booked ? "已订" : past ? "已过" : ""}</span>
                </button>
              );
            })}
          </div>
        </>
      )}

      {selectedSlot && court && (
        <div
          className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setSelectedSlot(null)}
        >
          <div
            className="w-full max-w-sm rounded-xl bg-white p-6 dark:bg-[#0a0a0a]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-4 text-base font-semibold">确认预定</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-black/60 dark:text-white/70">场地</dt>
                <dd>{court.name}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-black/60 dark:text-white/70">日期</dt>
                <dd>{selectedDate}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-black/60 dark:text-white/70">时段</dt>
                <dd>{selectedSlot}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-black/60 dark:text-white/70">价格</dt>
                <dd>{formatPrice(court.price)}</dd>
              </div>
            </dl>
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => setSelectedSlot(null)}
                disabled={submitting}
                className="flex-1 cursor-pointer rounded-full border border-black/[.08] py-2 text-sm transition-colors hover:border-black disabled:opacity-50 dark:border-white/[.145] dark:hover:border-white"
              >
                取消
              </button>
              <button
                onClick={handleConfirm}
                disabled={submitting}
                className="flex-1 cursor-pointer rounded-full bg-black py-2 text-sm font-medium text-white transition-colors hover:bg-black/80 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/80"
              >
                {submitting ? "预定中…" : "确认预定"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

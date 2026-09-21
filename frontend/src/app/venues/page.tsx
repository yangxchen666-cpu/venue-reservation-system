"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import { COURT_TYPES, type Court } from "@/lib/types";

function formatPrice(price: string | number): string {
  return `¥${Number(price).toFixed(2)}`;
}

/** "HH:MM:SS" → "HH:MM" */
function formatTime(t: string): string {
  return t.slice(0, 5);
}

export default function VenuesPage() {
  const [courts, setCourts] = useState<Court[]>([]);
  const [type, setType] = useState("");
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 筛选变化后防抖 300ms 重新请求；清理时中止在途请求，避免竞态覆盖
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams();
        if (type) params.set("type", type);
        if (priceMin) params.set("price_min", priceMin);
        if (priceMax) params.set("price_max", priceMax);
        const qs = params.toString();
        const data = await apiFetch<Court[]>(`/courts${qs ? `?${qs}` : ""}`, {
          signal: controller.signal,
        });
        setCourts(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "加载失败，请稍后重试");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 300);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [type, priceMin, priceMax]);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1.5 text-sm">
          类型
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="rounded-lg border border-black/[.08] bg-white px-3 py-2 outline-none focus:border-black dark:border-white/[.145] dark:bg-[#0a0a0a] dark:focus:border-white"
          >
            <option value="">全部</option>
            {COURT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          最低价格
          <input
            type="number"
            min="0"
            value={priceMin}
            onChange={(e) => setPriceMin(e.target.value)}
            placeholder="不限"
            className="w-28 rounded-lg border border-black/[.08] px-3 py-2 outline-none focus:border-black dark:border-white/[.145] dark:focus:border-white"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          最高价格
          <input
            type="number"
            min="0"
            value={priceMax}
            onChange={(e) => setPriceMax(e.target.value)}
            placeholder="不限"
            className="w-28 rounded-lg border border-black/[.08] px-3 py-2 outline-none focus:border-black dark:border-white/[.145] dark:focus:border-white"
          />
        </label>
        {(type || priceMin || priceMax) && (
          <button
            onClick={() => {
              setType("");
              setPriceMin("");
              setPriceMax("");
            }}
            className="cursor-pointer py-2 text-sm text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white"
          >
            清除筛选
          </button>
        )}
      </div>

      {loading && <p className="py-16 text-center text-black/60 dark:text-white/70">加载中…</p>}
      {!loading && error && (
        <p className="py-16 text-center text-red-600 dark:text-red-400">{error}</p>
      )}
      {!loading && !error && courts.length === 0 && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">暂无场地</p>
      )}
      {!loading && !error && courts.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {courts.map((court) => (
            <Link
              key={court.id}
              href={`/venues/${court.id}`}
              className="rounded-xl border border-black/[.08] p-5 transition-colors hover:border-black dark:border-white/[.145] dark:hover:border-white"
            >
              <div className="mb-2 flex items-baseline justify-between gap-2">
                <h2 className="text-base font-semibold">{court.name}</h2>
                <span className="text-sm text-black/60 dark:text-white/70">{court.type}</span>
              </div>
              <p className="text-lg font-medium">{formatPrice(court.price)}</p>
              <p className="mt-1 text-sm text-black/60 dark:text-white/70">
                开放时间 {formatTime(court.open_time)} - {formatTime(court.close_time)}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

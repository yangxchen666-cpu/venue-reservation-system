import Link from "next/link";

import { apiFetch, ApiError } from "@/lib/api";
import type { Court } from "@/lib/types";

interface PageProps {
  params: Promise<{ courtId: string }>;
}

function formatPrice(price: string | number): string {
  return `¥${Number(price).toFixed(2)}`;
}

/** "HH:MM:SS" → "HH:MM" */
function formatTime(t: string): string {
  return t.slice(0, 5);
}

/** 由开放时间与时段粒度生成预览文本，如「09:00-22:00，每 60 分钟一节」（SPEC-3） */
function slotPreview(court: Court): string {
  return `${formatTime(court.open_time)}-${formatTime(court.close_time)}，每 ${court.slot_minutes} 分钟一节`;
}

export default async function CourtDetailPage({ params }: PageProps) {
  const { courtId } = await params;

  let court: Court | null = null;
  let error = "";
  let isNotFound = false;

  const id = Number(courtId);
  if (!Number.isInteger(id) || id <= 0) {
    isNotFound = true;
  } else {
    try {
      court = await apiFetch<Court>(`/courts/${id}`, { cache: "no-store" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        isNotFound = true;
      } else {
        error = err instanceof ApiError ? err.message : "加载失败，请稍后重试";
      }
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href="/venues"
        className="mb-6 inline-block text-sm text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white"
      >
        ← 返回场地列表
      </Link>
      {isNotFound && (
        <p className="py-16 text-center text-black/60 dark:text-white/70">场地不存在</p>
      )}
      {!isNotFound && error && (
        <p className="py-16 text-center text-red-600 dark:text-red-400">{error}</p>
      )}
      {court && (
        <div className="rounded-xl border border-black/[.08] p-6 dark:border-white/[.145]">
          <div className="mb-6 flex items-baseline justify-between gap-2">
            <h1 className="text-2xl font-semibold">{court.name}</h1>
            <span className="text-sm text-black/60 dark:text-white/70">{court.type}</span>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex items-baseline justify-between">
              <dt className="text-black/60 dark:text-white/70">价格</dt>
              <dd className="text-lg font-medium">{formatPrice(court.price)}</dd>
            </div>
            <div className="flex items-baseline justify-between">
              <dt className="text-black/60 dark:text-white/70">开放时间</dt>
              <dd>
                {formatTime(court.open_time)} - {formatTime(court.close_time)}
              </dd>
            </div>
            <div className="flex items-baseline justify-between">
              <dt className="text-black/60 dark:text-white/70">时段划分</dt>
              <dd>{slotPreview(court)}</dd>
            </div>
          </dl>
          <Link
            href={`/book/${court.id}`}
            className="mt-6 block rounded-full bg-black py-2.5 text-center text-sm font-medium text-white transition-colors hover:bg-black/80 dark:bg-white dark:text-black dark:hover:bg-white/80"
          >
            去预定
          </Link>
        </div>
      )}
    </div>
  );
}

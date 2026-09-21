"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearToken, getUserRole, isLoggedIn } from "@/lib/auth";

interface NavItem {
  href: string;
  label: string;
  auth?: boolean; // 仅登录后显示
  roles?: string[]; // 仅指定角色显示
}

const NAV_ITEMS: NavItem[] = [
  { href: "/venues", label: "场地列表" },
  { href: "/orders", label: "我的预定", auth: true },
  { href: "/me", label: "个人中心", auth: true },
  { href: "/venue-admin", label: "场地管理员", roles: ["venue_admin", "admin"] },
  { href: "/admin", label: "系统后台", roles: ["admin"] },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);
  const [role, setRole] = useState<string | null>(null);

  // 挂载后读取 localStorage，避免 SSR 水合不一致；pathname 变化时重读（登录/退出跳转后同步）
  useEffect(() => {
    setLoggedIn(isLoggedIn());
    setRole(getUserRole());
  }, [pathname]);

  function handleLogout() {
    clearToken();
    router.push("/venues");
    setLoggedIn(false);
    setRole(null);
  }

  const visibleItems = NAV_ITEMS.filter((item) => {
    if (item.auth && !loggedIn) return false;
    if (item.roles && (!loggedIn || !role || !item.roles.includes(role))) return false;
    return true;
  });

  return (
    <header className="sticky top-0 z-10 border-b border-black/[.08] bg-white dark:border-white/[.145] dark:bg-[#0a0a0a]">
      <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3 text-sm">
        <Link href="/venues" className="text-base font-semibold">
          球场预定管理系统
        </Link>
        {visibleItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={
              pathname.startsWith(item.href)
                ? "font-medium"
                : "text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white"
            }
          >
            {item.label}
          </Link>
        ))}
        <div className="ml-auto flex items-center gap-4">
          {loggedIn ? (
            <button
              onClick={handleLogout}
              className="cursor-pointer text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white"
            >
              退出
            </button>
          ) : (
            <>
              <Link href="/login" className="text-black/60 hover:text-black dark:text-white/70 dark:hover:text-white">
                登录
              </Link>
              <Link
                href="/register"
                className="rounded-full bg-black px-4 py-1.5 text-white transition-colors hover:bg-black/80 dark:bg-white dark:text-black dark:hover:bg-white/80"
              >
                注册
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}

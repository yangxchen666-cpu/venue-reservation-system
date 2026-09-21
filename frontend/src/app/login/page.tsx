import type { Metadata } from "next";
import { Suspense } from "react";

import LoginForm from "./LoginForm";

export const metadata: Metadata = {
  title: "登录 - 球场预定管理系统",
};

export default function LoginPage() {
  return (
    <div className="mx-auto max-w-sm pt-12">
      <h1 className="mb-6 text-center text-2xl font-semibold">登录</h1>
      {/* useSearchParams 需要 Suspense 边界（Next 15 静态渲染要求） */}
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}

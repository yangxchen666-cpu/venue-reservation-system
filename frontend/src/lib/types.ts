// 与后端 app/schemas/ 对应的 TS 类型（JSON 序列化后的形态）

export type Role = "user" | "venue_admin" | "admin";

export interface User {
  id: number;
  username: string;
  role: Role;
  created_at: string; // ISO 8601 datetime
}

export type ApplicationStatus = "pending" | "approved" | "rejected";

/** GET /auth/me 响应（SPEC-D1：最近一次申请状态，无申请为 null） */
export interface MeResponse extends User {
  application_status: ApplicationStatus | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const COURT_TYPES = ["羽毛球", "篮球", "网球", "足球"] as const;

export interface Court {
  id: number;
  name: string;
  type: string;
  // Decimal：后端序列化可能为字符串或数字，展示时用 Number() 转
  price: string | number;
  open_time: string; // "HH:MM:SS"
  close_time: string; // "HH:MM:SS"
  slot_minutes: number; // 60 / 120 / 180
}

export type BookingStatus = "booked" | "checked_in" | "cancelled";

export interface Booking {
  id: number;
  user_id: number;
  court_id: number;
  date: string; // "YYYY-MM-DD"
  start_time: string; // "HH:MM:SS"
  status: BookingStatus;
  price: string | number | null;
  paid: boolean;
  created_at: string;
  court_name: string | null; // 列表接口 join Court 填充；创建响应为 null
}

/** venue_admin / admin 管理视图：Booking + username */
export interface AdminBooking extends Booking {
  username: string;
}

"use client";

import * as React from "react";

export type Notification = {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  isRead: boolean;
  type?: "info" | "warning" | "success" | "error";
};

const INITIAL_NOTIFICATIONS: Notification[] = [
  {
    id: "1",
    title: "Cảnh báo rủi ro mới",
    message: "Sinh viên Nguyễn Văn An có dấu hiệu rủi ro cao trong tuần này.",
    timestamp: "2 phút trước",
    isRead: false,
    type: "warning",
  },
  {
    id: "2",
    title: "Lịch hẹn sắp tới",
    message: "Bạn có buổi tư vấn với lớp K21 vào lúc 14:00 hôm nay.",
    timestamp: "1 giờ trước",
    isRead: false,
    type: "info",
  },
  {
    id: "3",
    title: "Cập nhật dữ liệu thành công",
    message: "Dữ liệu điểm thi học kỳ 1 đã được đồng bộ hoàn tất.",
    timestamp: "5 giờ trước",
    isRead: true,
    type: "success",
  },
  {
    id: "4",
    title: "Báo cáo hàng tuần",
    message: "Báo cáo tổng hợp tuần 15 đã sẵn sàng để xem.",
    timestamp: "Hôm qua",
    isRead: true,
    type: "info",
  },
];

export function useNotifications() {
  const [notifications, setNotifications] = React.useState<Notification[]>(
    INITIAL_NOTIFICATIONS
  );

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
    );
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
  };

  const clearNotifications = () => {
    setNotifications([]);
  };

  return {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  };
}

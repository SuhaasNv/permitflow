import { request } from './client'

export interface NotificationItem {
  id: string
  application_id: string
  kind: 'submitted' | 'resubmitted' | 'status_changed'
  title: string
  body: string
  read_at: string | null
  created_at: string
}

export interface Notifications {
  items: NotificationItem[]
  unread_count: number
}

export function getNotifications(): Promise<Notifications> {
  return request<Notifications>('/notifications')
}

export function markNotificationRead(id: string): Promise<NotificationItem> {
  return request<NotificationItem>(`/notifications/${id}/read`, { method: 'POST' })
}

export function markAllNotificationsRead(): Promise<Notifications> {
  return request<Notifications>('/notifications/read-all', { method: 'POST' })
}

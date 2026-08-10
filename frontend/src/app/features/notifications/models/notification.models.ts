import type { PaginatedResponse } from '../../../core/models/application.models';

export type NotificationType = 'SYSTEM' | 'USER' | 'DOCUMENT' | 'SECURITY' | 'ADMIN';
export type NotificationLevel = 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';
export interface NotificationItem { id:number; title:string; message:string; type:NotificationType; type_display:string; level:NotificationLevel; level_display:string; action_url:string; read:boolean; read_at:string|null; created_at:string; expires_at:string|null; }
export interface NotificationQuery { read?:string; type?:string; level?:string; dateFrom?:string; dateTo?:string; page?:number; ordering?:string; }
export type NotificationPage = PaginatedResponse<NotificationItem>;

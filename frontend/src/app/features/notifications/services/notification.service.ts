import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin, tap } from 'rxjs';
import { NotificationItem, NotificationPage, NotificationQuery } from '../models/notification.models';

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly http=inject(HttpClient); private readonly router=inject(Router);
  readonly recent=signal<NotificationItem[]>([]); readonly unreadCount=signal(0); readonly loading=signal(false);
  list(query:NotificationQuery={}) { let params=new HttpParams(); const values:Record<string,string|number|undefined>={read:query.read,type:query.type,level:query.level,date_from:query.dateFrom,date_to:query.dateTo,page:query.page,ordering:query.ordering}; Object.entries(values).forEach(([key,value])=>{if(value!==undefined&&value!=='')params=params.set(key,value)}); return this.http.get<NotificationPage>('/api/notifications/',{params}); }
  refresh() { this.loading.set(true); return forkJoin({page:this.list({ordering:'-created_at'}),count:this.http.get<{count:number}>('/api/notifications/unread-count/')}).pipe(tap(({page,count})=>{this.recent.set(page.results.slice(0,5));this.unreadCount.set(count.count);this.loading.set(false)})); }
  markRead(item:NotificationItem) { if(item.read)return this.http.get<NotificationItem>(`/api/notifications/${item.id}/`); return this.http.patch<NotificationItem>(`/api/notifications/${item.id}/read/`,{}).pipe(tap(updated=>{this.recent.update(items=>items.map(value=>value.id===updated.id?updated:value));this.unreadCount.update(count=>Math.max(0,count-1))})); }
  readAll() { return this.http.post<{updated:number}>('/api/notifications/read-all/',{}).pipe(tap(()=>{this.recent.update(items=>items.map(item=>({...item,read:true})));this.unreadCount.set(0)})); }
  open(item:NotificationItem) { this.markRead(item).subscribe({next:()=>{if(!item.action_url)return;if(item.action_url.startsWith('/'))this.router.navigateByUrl(item.action_url);else {const opened=window.open(item.action_url,'_blank','noopener,noreferrer');if(opened)opened.opener=null;}}}); }
}

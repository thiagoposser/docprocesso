import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { Payment, PaymentMethod, PaymentPage, PaymentPayload, PaymentQuery, PaymentReceipt, ReceiptAttachment, Supplier, SupplierPage } from '../models/payment.models';

@Injectable({ providedIn: 'root' })
export class PaymentService {
  private readonly http = inject(HttpClient);
  list(query: PaymentQuery = {}) { let params = new HttpParams().set('ordering', query.ordering || 'due_date'); const values: Record<string, string | number | undefined> = { search: query.search, process: query.process, status: query.status, sector: query.sector, supplier: query.supplier, due_from: query.dueFrom, due_to: query.dueTo, min_amount: query.minAmount, max_amount: query.maxAmount, page: query.page }; for (const [key, value] of Object.entries(values)) if (value !== undefined && value !== '') params = params.set(key, value); return this.http.get<PaymentPage>('/api/payments/', { params }); }
  get(id: number) { return this.http.get<Payment>(`/api/payments/${id}/`); }
  create(payload: PaymentPayload) { return this.http.post<Payment>('/api/payments/', payload); }
  update(id: number, payload: Partial<PaymentPayload>) { return this.http.patch<Payment>(`/api/payments/${id}/`, payload); }
  suppliers(search = '') { return this.http.get<SupplierPage>('/api/suppliers/', { params: { search } }); }
  schedule(id: number, scheduledAt: string) { return this.http.post<Payment>(`/api/payments/${id}/schedule/`, { scheduled_at: scheduledAt }); }
  confirm(id: number, payload: { paid_at: string; paid_amount: string; payment_method: PaymentMethod }) { return this.http.post<Payment>(`/api/payments/${id}/confirm/`, payload); }
  cancel(id: number, reason: string) { return this.http.post<Payment>(`/api/payments/${id}/cancel/`, { reason }); }
  receipts(id: number) { return this.http.get<PaymentReceipt[]>(`/api/payments/${id}/receipts/`); }
  addReceipt(id: number, file: File) { const payload = new FormData(); payload.set('file', file); return this.http.post<PaymentReceipt>(`/api/payments/${id}/receipts/`, payload); }
  downloadReceipt(attachmentId: number) { return this.http.get(`/api/attachments/${attachmentId}/download/`, { responseType: 'blob' }); }
  deactivateReceipt(attachmentId: number) { return this.http.patch<ReceiptAttachment>(`/api/attachments/${attachmentId}/deactivate/`, {}); }
}

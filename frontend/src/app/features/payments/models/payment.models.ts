import type { PaginatedResponse } from '../../../core/models/application.models';

export type PaymentStatus = 'PENDING' | 'SCHEDULED' | 'PAID' | 'CANCELLED';
export type PaymentMethod = 'PIX' | 'BANK_TRANSFER' | 'BOLETO' | 'CARD' | 'CASH' | 'OTHER';

export interface Supplier { id: number; name: string; tax_id_masked: string; tax_id?: string; email?: string; phone?: string; bank_name?: string; bank_branch?: string; bank_account?: string; active: boolean; }
export interface Payment { id: number; process: number; process_number: string; document: number | null; sector: number; sector_name: string; supplier: number; supplier_name: string; description: string; amount: string; due_date: string; status: PaymentStatus; is_overdue: boolean; scheduled_at: string | null; paid_at: string | null; paid_amount: string | null; payment_method: PaymentMethod | ''; paid_by: number | null; cancelled_at: string | null; cancellation_reason: string; created_at: string; updated_at: string; }
export interface PaymentPayload { process: number; document?: number | null; sector: number; supplier: number; description: string; amount: string; due_date: string; }
export interface ReceiptAttachment { id: number; file_name: string | null; download_url: string | null; source_type: 'file' | 'external_url'; active: boolean; created_at: string; deactivated_at: string | null; }
export interface PaymentReceipt { id: number; payment: number; attachment: ReceiptAttachment; created_by: number; created_at: string; }
export type PaymentDeadline = 'overdue' | 'today' | 'upcoming';
export interface PaymentDeadlineSummary { overdue: number; today: number; upcoming: number; }
export interface PaymentQuery { search?: string; process?: string; status?: string; deadline?: string; sector?: string; supplier?: string; dueFrom?: string; dueTo?: string; minAmount?: string; maxAmount?: string; ordering?: string; page?: number; }
export type PaymentPage = PaginatedResponse<Payment>;
export type SupplierPage = PaginatedResponse<Supplier>;

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = { PENDING: 'Pendente', SCHEDULED: 'Agendado', PAID: 'Pago', CANCELLED: 'Cancelado' };
export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = { PIX: 'Pix', BANK_TRANSFER: 'Transferência bancária', BOLETO: 'Boleto', CARD: 'Cartão', CASH: 'Dinheiro', OTHER: 'Outro' };

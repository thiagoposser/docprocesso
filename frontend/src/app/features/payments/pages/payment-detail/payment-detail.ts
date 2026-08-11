import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { PAYMENT_METHOD_LABELS, PAYMENT_STATUS_LABELS, Payment, PaymentMethod } from '../../models/payment.models';
import { PaymentService } from '../../services/payment.service';

@Component({
  selector: 'app-payment-detail', imports: [CurrencyPipe, DatePipe, ReactiveFormsModule, RouterLink, PageHeader],
  template: `
    <app-page-header title="Detalhes do pagamento" description="Consulte e execute ações financeiras autorizadas."><a class="btn btn-outline-secondary" routerLink="/pagamentos">Voltar</a>@if (canEdit()) { <a class="btn btn-primary" [routerLink]="['/pagamentos', payment()!.id, 'editar']">Editar</a> }</app-page-header>
    @if (error()) { <div class="alert alert-danger">{{ error() }}</div> }
    @if (payment(); as item) {
      <section class="card border-0 shadow-sm"><div class="card-body p-4"><div class="d-flex justify-content-between"><div><small>{{ item.process_number }}</small><h2 class="h4">{{ item.description }}</h2></div><span class="badge align-self-start" [class]="statusClass(item)">{{ labels[item.status] }}{{ item.is_overdue ? ' · Vencido' : '' }}</span></div><dl class="row mb-0"><dt class="col-sm-4">Fornecedor</dt><dd class="col-sm-8">{{ item.supplier_name }}</dd><dt class="col-sm-4">Setor</dt><dd class="col-sm-8">{{ item.sector_name }}</dd><dt class="col-sm-4">Valor</dt><dd class="col-sm-8">{{ item.amount | currency:'BRL':'symbol':'1.2-2':'pt-BR' }}</dd><dt class="col-sm-4">Vencimento</dt><dd class="col-sm-8">{{ item.due_date | date:'longDate' }}</dd>@if (item.scheduled_at) { <dt class="col-sm-4">Agendado para</dt><dd class="col-sm-8">{{ item.scheduled_at | date:'short' }}</dd> }@if (item.paid_at) { <dt class="col-sm-4">Pago em</dt><dd class="col-sm-8">{{ item.paid_at | date:'short' }} · {{ item.paid_amount | currency:'BRL':'symbol':'1.2-2':'pt-BR' }} · {{ paymentMethodLabel(item.payment_method) }}</dd> }@if (item.cancellation_reason) { <dt class="col-sm-4">Motivo do cancelamento</dt><dd class="col-sm-8">{{ item.cancellation_reason }}</dd> }</dl></div></section>
      @if (item.status === 'PENDING' || item.status === 'SCHEDULED') {
        <section class="card border-0 shadow-sm mt-4"><div class="card-header bg-white"><h2 class="h5 mb-0">Ações financeiras</h2></div><div class="card-body"><div class="d-flex flex-wrap gap-2 mb-3">@if (item.status === 'PENDING' && can('payments.schedule_payment')) { <button class="btn btn-outline-primary" (click)="action.set('schedule')">Agendar</button> }@if (can('payments.confirm_payment')) { <button class="btn btn-success" (click)="action.set('confirm')">Confirmar pagamento</button> }@if (can('payments.cancel_payment')) { <button class="btn btn-outline-danger" (click)="action.set('cancel')">Cancelar</button> }</div>
        @if (action() === 'schedule') { <form [formGroup]="scheduleForm" (ngSubmit)="schedule()"><label class="form-label">Data do agendamento</label><input type="datetime-local" class="form-control" formControlName="scheduled_at"><button class="btn btn-primary mt-3" [disabled]="saving()">Confirmar agendamento</button></form> }
        @if (action() === 'confirm') { <form [formGroup]="confirmForm" (ngSubmit)="confirm()"><div class="row g-3"><div class="col-md-4"><label class="form-label">Data do pagamento</label><input type="datetime-local" class="form-control" formControlName="paid_at"></div><div class="col-md-4"><label class="form-label">Valor pago</label><input class="form-control" inputmode="decimal" formControlName="paid_amount"></div><div class="col-md-4"><label class="form-label">Forma</label><select class="form-select" formControlName="payment_method"><option value="">Selecione</option>@for (method of methods; track method) { <option [value]="method">{{ methodLabels[method] }}</option> }</select></div></div><button class="btn btn-success mt-3" [disabled]="saving()">Confirmar pagamento</button></form> }
        @if (action() === 'cancel') { <form [formGroup]="cancelForm" (ngSubmit)="cancel()"><label class="form-label">Motivo</label><textarea class="form-control" rows="3" maxlength="2000" formControlName="reason"></textarea><button class="btn btn-danger mt-3" [disabled]="saving()">Confirmar cancelamento</button></form> }
        </div></section>
      }
    }
  `
})
export class PaymentDetail {
  readonly auth = inject(AuthService); private readonly api = inject(PaymentService); private readonly route = inject(ActivatedRoute); private readonly id = Number(this.route.snapshot.paramMap.get('id'));
  readonly payment = signal<Payment | null>(null); readonly error = signal(''); readonly saving = signal(false); readonly action = signal<'schedule' | 'confirm' | 'cancel' | null>(null); readonly labels = PAYMENT_STATUS_LABELS; readonly methodLabels = PAYMENT_METHOD_LABELS; readonly methods = Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[];
  readonly scheduleForm = new FormGroup({ scheduled_at: new FormControl('', { nonNullable: true, validators: [Validators.required] }) });
  readonly confirmForm = new FormGroup({ paid_at: new FormControl('', { nonNullable: true, validators: [Validators.required] }), paid_amount: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.pattern(/^\d{1,12}([.,]\d{1,2})?$/)] }), payment_method: new FormControl('', { nonNullable: true, validators: [Validators.required] }) });
  readonly cancelForm = new FormGroup({ reason: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.maxLength(2000)] }) });
  constructor() { this.load(); }
  can(permission: string) { const item = this.payment(); return Boolean(item && this.auth.canInSector(permission, item.sector)); }
  canEdit() { const item = this.payment(); return Boolean(item && ['PENDING', 'SCHEDULED'].includes(item.status) && this.can('payments.change_payment')); }
  statusClass(item: Payment) { return `text-bg-${item.status === 'PAID' ? 'success' : item.status === 'CANCELLED' ? 'secondary' : item.is_overdue ? 'danger' : item.status === 'SCHEDULED' ? 'info' : 'warning'}`; }
  paymentMethodLabel(method: PaymentMethod | '') { return method ? this.methodLabels[method] : ''; }
  schedule() { if (this.scheduleForm.invalid) return; this.execute(() => this.api.schedule(this.id, new Date(this.scheduleForm.getRawValue().scheduled_at).toISOString()), 'agendamento'); }
  confirm() { if (this.confirmForm.invalid || !window.confirm('Confirmar definitivamente este pagamento?')) return; const value = this.confirmForm.getRawValue(); this.execute(() => this.api.confirm(this.id, { paid_at: new Date(value.paid_at).toISOString(), paid_amount: value.paid_amount.replace(',', '.'), payment_method: value.payment_method as PaymentMethod }), 'confirmação'); }
  cancel() { if (this.cancelForm.invalid || !window.confirm('Cancelar este pagamento?')) return; this.execute(() => this.api.cancel(this.id, this.cancelForm.getRawValue().reason.trim()), 'cancelamento'); }
  private execute(request: () => ReturnType<PaymentService['get']>, label: string) { this.saving.set(true); this.error.set(''); request().pipe(finalize(() => this.saving.set(false))).subscribe({ next: item => { this.payment.set(item); this.action.set(null); }, error: response => { if (response?.status === 409) this.load(); this.error.set(response?.status === 409 ? 'O pagamento já foi alterado. Os dados foram recarregados; revise antes de tentar novamente.' : response?.status === 403 ? 'Você não possui permissão para esta ação.' : `Não foi possível concluir o ${label}.`); } }); }
  private load() { this.api.get(this.id).subscribe({ next: item => { this.payment.set(item); this.confirmForm.patchValue({ paid_amount: item.amount }); }, error: response => this.error.set(response?.status === 403 ? 'Você não possui acesso aos dados financeiros.' : 'Pagamento não encontrado ou fora do seu escopo.') }); }
}

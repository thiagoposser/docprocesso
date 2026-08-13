import { Component, effect, inject, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';

import { ProcessItem, WorkflowAction } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-actions', imports: [ReactiveFormsModule],
  template: `
    <section class="card border-0 shadow-sm mt-4" aria-labelledby="actions-title">
      <div class="card-header bg-white p-3 d-flex justify-content-between align-items-center"><h2 id="actions-title" class="h5 mb-0">Ações disponíveis</h2>@if (loading()) { <span class="spinner-border spinner-border-sm" aria-label="Carregando ações"></span> }</div>
      <div class="card-body p-4">
        @if (loadError()) { <div class="alert alert-danger mb-0" role="alert">{{ loadError() }} <button class="btn btn-sm btn-outline-danger ms-2" type="button" (click)="loadActions()">Tentar novamente</button></div> }
        @else if (!loading() && !actions().length) { <p class="text-body-secondary mb-0">Nenhuma ação disponível para você nesta etapa.</p> }
        @else {
          <div class="d-flex flex-wrap gap-2 mb-3">@for (option of actions(); track option.action) { <button class="btn btn-sm" [class.btn-primary]="selected()?.action === option.action" [class.btn-outline-primary]="selected()?.action !== option.action" type="button" [disabled]="saving()" (click)="select(option)">{{ option.label }}</button> }</div>
          @if (selected(); as option) {
            <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
              <p class="mb-2"><strong>Próxima etapa:</strong> {{ option.destination_stage_name }}</p>
              @if (option.requires_attachment) { <div class="alert alert-info py-2" role="status">Esta ação exige {{ option.required_document_role === 'PAYMENT_RECEIPT' ? 'um comprovante de pagamento' : 'ao menos um documento ou anexo ativo' }}. Use a seção de documentos antes de confirmar.</div> }
              <label class="form-label" for="action-note">Observação{{ option.requires_note ? ' (obrigatória)' : ' (opcional)' }}</label><textarea id="action-note" class="form-control" rows="3" maxlength="2000" formControlName="note" [class.is-invalid]="form.controls.note.invalid && form.controls.note.touched"></textarea><div class="invalid-feedback">Informe a observação exigida para esta ação.</div>
              @if (!selectionValid()) { <div class="alert alert-warning mt-3 mb-0" role="alert">Esta ação não está mais disponível. O texto foi preservado para revisão.</div> }
              @if (error()) { <div class="alert alert-danger mt-3 mb-0" role="alert">{{ error() }}</div> }
              <div class="d-flex justify-content-end gap-2 mt-3"><button class="btn btn-light" type="button" [disabled]="saving()" (click)="cancelSelection()">Cancelar</button><button class="btn btn-primary" type="submit" [disabled]="saving() || !selectionValid()">{{ saving() ? 'Executando…' : 'Confirmar ' + option.label.toLowerCase() }}</button></div>
            </form>
          }
        }
      </div>
    </section>
  `
})
export class ProcessActions {
  private readonly fb = inject(FormBuilder); private readonly api = inject(ProcessService);
  readonly process = input.required<ProcessItem>(); readonly updated = output<ProcessItem>(); readonly conflict = output<void>();
  readonly actions = signal<WorkflowAction[]>([]); readonly selected = signal<WorkflowAction | null>(null);
  readonly loading = signal(true); readonly saving = signal(false); readonly loadError = signal(''); readonly error = signal('');
  readonly form = this.fb.nonNullable.group({ note: [''] });

  constructor() { effect(() => { this.process().version; this.loadActions(); }); }
  selectionValid() { const selected = this.selected(); return !selected || this.actions().some(option => option.action === selected.action); }
  loadActions() { this.loading.set(true); this.loadError.set(''); this.api.availableActions(this.process().id).subscribe({ next: actions => { this.actions.set(actions); this.loading.set(false); }, error: () => { this.loadError.set('Não foi possível carregar as ações autorizadas.'); this.loading.set(false); } }); }
  select(option: WorkflowAction) { this.selected.set(option); this.error.set(''); this.form.controls.note.setValidators(option.requires_note ? Validators.required : null); this.form.controls.note.updateValueAndValidity(); }
  cancelSelection() { this.selected.set(null); this.error.set(''); this.form.reset(); }
  submit() { const option = this.selected(); if (!option || this.saving()) return; this.form.markAllAsTouched(); if (this.form.invalid) { this.error.set('Preencha os campos obrigatórios.'); return; } if (!this.selectionValid()) { this.error.set('A ação não está mais disponível. Recarregue o processo.'); return; } if (!window.confirm(`Confirmar a ação “${option.label}”?`)) return; this.saving.set(true); this.error.set(''); this.api.executeTransition(this.process().id, { action: option.action, version: this.process().version, note: this.form.controls.note.value.trim() }).pipe(finalize(() => this.saving.set(false))).subscribe({ next: process => { this.cancelSelection(); this.actions.set([]); this.updated.emit(process); }, error: response => { if (response?.status === 409) { this.error.set('O processo foi alterado por outro usuário. Os dados foram recarregados; revise antes de tentar novamente.'); this.conflict.emit(); } else if (response?.status === 422) this.error.set(response?.error?.detail === 'attachment_required' ? 'Inclua um documento ou anexo ativo antes de executar esta ação.' : 'Informe a observação obrigatória.'); else if (response?.status === 403) { this.error.set('Esta ação não está mais autorizada para você.'); this.loadActions(); } else this.error.set(response?.error?.detail || 'Não foi possível executar a ação.'); } }); }
}

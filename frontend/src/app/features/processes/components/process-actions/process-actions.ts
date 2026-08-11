import { Component, computed, inject, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { FlatSectorNode } from '../../../sectors/models/sector.models';
import { ProcessAction, ProcessItem } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

interface ActionOption { action: ProcessAction; label: string; permission: string; states: string[]; destination?: boolean; noteRequired?: boolean; manager?: boolean; }

@Component({
  selector: 'app-process-actions', imports: [ReactiveFormsModule],
  template: `
    @if (available().length) { <section class="card border-0 shadow-sm mt-4" aria-labelledby="actions-title"><div class="card-header bg-white p-3"><h2 id="actions-title" class="h5 mb-0">Ações disponíveis</h2></div><div class="card-body p-4"><div class="d-flex flex-wrap gap-2 mb-3">@for (option of available(); track option.action) { <button class="btn btn-sm" [class.btn-primary]="selected()?.action === option.action" [class.btn-outline-primary]="selected()?.action !== option.action" type="button" (click)="select(option)">{{ option.label }}</button> }</div>
      @if (selected(); as option) { <form [formGroup]="form" (ngSubmit)="submit()" novalidate><div class="row g-3">@if (option.destination) { <div class="col-12 col-md-6"><label class="form-label" for="action-destination">Setor de destino</label><select id="action-destination" class="form-select" formControlName="destination"><option value="">Selecione</option>@for (sector of sectors(); track sector.id) { @if (sector.id !== process().current_sector) { <option [value]="sector.id">{{ '— '.repeat(sector.level) }}{{ sector.name }}</option> } }</select></div> }<div class="col-12" [class.col-md-6]="option.destination"><label class="form-label" for="action-note">Observação{{ option.noteRequired ? ' (obrigatória)' : ' (opcional)' }}</label><textarea id="action-note" class="form-control" rows="3" maxlength="2000" formControlName="note"></textarea></div></div>@if (!selectionValid()) { <div class="alert alert-warning mt-3 mb-0" role="alert">Esta ação não é mais válida. O texto foi preservado.</div> }@if (error()) { <div class="alert alert-danger mt-3 mb-0" role="alert">{{ error() }}</div> }<div class="d-flex justify-content-end gap-2 mt-3"><button class="btn btn-light" type="button" (click)="cancelSelection()">Cancelar</button><button class="btn btn-primary" type="submit" [disabled]="saving() || !selectionValid()">{{ saving() ? 'Executando…' : 'Confirmar ' + option.label.toLowerCase() }}</button></div></form> }
    </div></section> }
  `
})
export class ProcessActions {
  private readonly fb = inject(FormBuilder); private readonly api = inject(ProcessService); readonly auth = inject(AuthService);
  readonly process = input.required<ProcessItem>(); readonly sectors = input.required<FlatSectorNode[]>(); readonly lastAction = input<string | null>(null); readonly updated = output<ProcessItem>(); readonly conflict = output<void>();
  readonly selected = signal<ActionOption | null>(null); readonly saving = signal(false); readonly error = signal('');
  readonly form = this.fb.nonNullable.group({ destination: [''], note: [''] });
  private readonly options: ActionOption[] = [
    { action: 'open', label: 'Abrir', permission: 'processes.open_administrativeprocess', states: ['DRAFT'] },
    { action: 'forward', label: 'Encaminhar', permission: 'processes.forward_administrativeprocess', states: ['OPEN', 'IN_PROGRESS'], destination: true },
    { action: 'receive', label: 'Receber', permission: 'processes.receive_administrativeprocess', states: ['IN_PROGRESS'] },
    { action: 'return', label: 'Devolver', permission: 'processes.return_administrativeprocess', states: ['IN_PROGRESS'], destination: true, noteRequired: true },
    { action: 'complete', label: 'Concluir', permission: 'processes.complete_administrativeprocess', states: ['OPEN', 'IN_PROGRESS'] },
    { action: 'reopen', label: 'Reabrir', permission: 'processes.reopen_administrativeprocess', states: ['COMPLETED'], noteRequired: true, manager: true },
    { action: 'cancel', label: 'Cancelar', permission: 'processes.cancel_administrativeprocess', states: ['OPEN', 'IN_PROGRESS'], noteRequired: true },
    { action: 'archive', label: 'Arquivar', permission: 'processes.archive_administrativeprocess', states: ['COMPLETED', 'CANCELLED'] },
  ];
  readonly available = computed(() => { const process = this.process(); const sector = process.current_sector || process.origin_sector; return this.options.filter(option => option.states.includes(process.status) && (option.action !== 'receive' || ['FORWARD', 'RETURN'].includes(this.lastAction() || '')) && this.auth.canInSector(option.permission, sector, Boolean(option.manager))); });
  readonly selectionValid = computed(() => { const selected = this.selected(); return !selected || this.available().some(option => option.action === selected.action); });
  select(option: ActionOption) { this.selected.set(option); this.error.set(''); this.form.controls.destination.setValidators(option.destination ? Validators.required : null); this.form.controls.note.setValidators(option.noteRequired ? Validators.required : null); this.form.updateValueAndValidity(); }
  cancelSelection() { this.selected.set(null); this.error.set(''); this.form.reset(); }
  submit() { const option = this.selected(); if (!option || this.saving()) return; if (!this.selectionValid()) { this.error.set('Esta ação não é mais válida para o estado atual. O texto foi preservado para revisão.'); return; } this.form.markAllAsTouched(); if (this.form.invalid) { this.error.set('Preencha os campos obrigatórios.'); return; } if (!window.confirm(`Confirmar a ação “${option.label}”?`)) return; const value = this.form.getRawValue(); this.saving.set(true); this.error.set(''); this.api.action(this.process().id, option.action, { version: this.process().version, destination: value.destination ? Number(value.destination) : undefined, note: value.note.trim() }).pipe(finalize(() => this.saving.set(false))).subscribe({ next: process => { this.updated.emit(process); this.cancelSelection(); }, error: response => { if (response?.status === 409) { this.error.set('O processo foi alterado por outro usuário. Os dados foram recarregados; revise e tente novamente.'); this.conflict.emit(); } else if (response?.status === 403) this.error.set('Você não possui permissão para esta ação.'); else if (response?.status === 404) this.error.set('Processo não encontrado ou fora do seu escopo.'); else this.error.set(response?.error?.detail || 'Não foi possível executar a ação.'); } }); }
}

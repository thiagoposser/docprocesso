import { Component, inject, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';

import { EligibleAssignee, ProcessItem } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-assignment', imports: [ReactiveFormsModule],
  template: `
    <section class="card border-0 shadow-sm mt-4" aria-labelledby="assignment-title"><div class="card-header bg-white p-3"><h2 id="assignment-title" class="h5 mb-0">Atribuição individual</h2></div><div class="card-body p-4">
      <form [formGroup]="form" (ngSubmit)="submit()"><label class="form-label" for="assignee-search">Pesquisar pessoa elegível</label><div class="input-group mb-3"><input id="assignee-search" class="form-control" formControlName="search" placeholder="Nome ou usuário"><button class="btn btn-outline-secondary" type="button" [disabled]="loading()" (click)="load()">Pesquisar</button></div>
      <label class="form-label" for="assignee">Responsável</label><select id="assignee" class="form-select" formControlName="assignee"><option value="">Selecione</option>@for (user of users(); track user.id) { <option [value]="user.id">{{ user.name || user.username }}</option> }</select>
      @if (error()) { <div class="alert alert-danger mt-3 mb-0">{{ error() }}</div> }<div class="d-flex justify-content-end mt-3"><button class="btn btn-primary" type="submit" [disabled]="saving() || form.controls.assignee.invalid">{{ saving() ? 'Atribuindo…' : 'Atribuir' }}</button></div></form>
    </div></section>
  `,
})
export class ProcessAssignment {
  private readonly fb = inject(FormBuilder); private readonly api = inject(ProcessService);
  readonly process = input.required<ProcessItem>(); readonly updated = output<ProcessItem>(); readonly conflict = output<void>();
  readonly users = signal<EligibleAssignee[]>([]); readonly loading = signal(false); readonly saving = signal(false); readonly error = signal('');
  readonly form = this.fb.nonNullable.group({ search: [''], assignee: ['', Validators.required] });
  constructor() { queueMicrotask(() => this.load()); }
  load() { this.loading.set(true); this.error.set(''); this.api.eligibleAssignees(this.process().id, this.form.controls.search.value.trim()).pipe(finalize(() => this.loading.set(false))).subscribe({ next: users => this.users.set(users), error: () => this.error.set('Não foi possível consultar as pessoas elegíveis.') }); }
  submit() { if (this.form.invalid || this.saving()) return; this.saving.set(true); this.error.set(''); this.api.assign(this.process().id, Number(this.form.controls.assignee.value), this.process().version).pipe(finalize(() => this.saving.set(false))).subscribe({ next: item => this.updated.emit(item), error: response => { if (response?.status === 409) { this.error.set('O processo foi alterado. Revise os dados atualizados.'); this.conflict.emit(); } else if (response?.status === 403) this.error.set('A pessoa selecionada não é mais elegível ou a atribuição não é permitida.'); else this.error.set('Não foi possível atribuir o processo.'); } }); }
}

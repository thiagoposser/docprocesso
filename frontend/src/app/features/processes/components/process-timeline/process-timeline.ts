import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';

import { ProcessMovement } from '../../models/process.models';

@Component({
  selector: 'app-process-timeline', imports: [DatePipe],
  template: `
    <section class="card border-0 shadow-sm mt-4" aria-labelledby="timeline-title"><div class="card-header bg-white p-3"><h2 id="timeline-title" class="h5 mb-0">Histórico de tramitação</h2></div><div class="card-body p-4">
      @if (loading()) { <div class="text-center text-body-secondary py-4">Carregando histórico…</div> }
      @for (item of movements(); track item.id) { <article class="timeline-item pb-4" [class.functional-event]="item.kind === 'event'"><div class="timeline-marker" aria-hidden="true"></div><div><div class="d-flex flex-column flex-sm-row justify-content-between gap-1"><strong>{{ item.title }}</strong><time class="text-body-secondary small">{{ item.created_at | date:'medium' }}</time></div><div class="small text-body-secondary mb-1">{{ item.actor_name || 'Sistema' }}@if (item.kind === 'movement') { <span> · {{ item.status_before_label }} → {{ item.status_after_label }}</span> } @else { <span> · {{ item.event_type_label }}</span> }</div>@if (item.from_sector_name || item.to_sector_name) { <div class="small"><span>{{ item.from_sector_name || 'Sem origem' }}</span> → <span>{{ item.to_sector_name || 'Sem destino' }}</span></div> }@if (item.note) { <p class="mt-2 mb-0">{{ item.note }}</p> }</div></article> }
      @empty { @if (!loading()) { <div class="text-center text-body-secondary py-4">Nenhuma movimentação registrada.</div> } }
    </div>@if (count() > movements().length) { <div class="card-footer bg-white d-flex justify-content-between align-items-center"><small>{{ movements().length }} de {{ count() }} eventos</small><div class="btn-group btn-group-sm"><button class="btn btn-outline-secondary" type="button" [disabled]="page() === 1" (click)="pageChange.emit(page() - 1)">Anterior</button><button class="btn btn-outline-secondary" type="button" [disabled]="!hasNext()" (click)="pageChange.emit(page() + 1)">Próxima</button></div></div> }
    </section>
  `,
  styles: [`.timeline-item{position:relative;padding-left:1.75rem;border-left:2px solid #e5e7eb}.timeline-item:last-child{padding-bottom:0!important}.timeline-marker{position:absolute;left:-.42rem;top:.2rem;width:.72rem;height:.72rem;border-radius:50%;background:var(--color-primary);border:2px solid #fff;box-shadow:0 0 0 1px var(--color-primary)}.functional-event .timeline-marker{background:var(--color-success);box-shadow:0 0 0 1px var(--color-success)}`]
})
export class ProcessTimeline {
  readonly movements = input.required<ProcessMovement[]>(); readonly loading = input(false); readonly count = input(0); readonly page = input(1); readonly hasNext = input(false); readonly pageChange = output<number>();
}

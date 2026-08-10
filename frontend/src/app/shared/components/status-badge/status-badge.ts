import { Component, input } from '@angular/core';

@Component({
  selector: 'app-status-badge',
  template: `<span class="status" [class.active]="active()"><i></i>{{ active() ? 'Ativo' : 'Inativo' }}</span>`,
  styles: [`.status{display:inline-flex;align-items:center;gap:.35rem;padding:.28rem .5rem;border-radius:2rem;color:var(--color-text-muted);background:#f1f2f4;font-size:.7rem;font-weight:620}.status i{width:.38rem;height:.38rem;border-radius:50%;background:#9aa0aa}.status.active{color:#107052;background:#edf8f3}.status.active i{background:var(--color-success)}`]
})
export class StatusBadge { readonly active = input.required<boolean>(); }

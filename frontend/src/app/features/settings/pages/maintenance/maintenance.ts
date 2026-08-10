import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { SettingsService } from '../../services/settings.service';

@Component({
  selector: 'app-maintenance',
  template: `<main class="maintenance-page"><section class="card border-0 shadow-sm text-center"><div class="card-body p-5">@if (settings.logoUrl()) { <img class="logo mb-4" [src]="settings.logoUrl()" alt=""> } @else { <div class="mark mx-auto mb-4">{{ settings.shortName() }}</div> }<h1 class="h3">Sistema em manutenção</h1><p class="text-body-secondary">Estamos realizando ajustes no {{ settings.name() }}. Tente novamente em alguns instantes.</p><button class="btn btn-primary mt-2" type="button" (click)="retry()">Tentar novamente</button></div></section></main>`,
  styles: [`.maintenance-page{min-height:100vh;display:grid;place-items:center;padding:1.5rem;background:var(--color-background)}.card{width:min(100%,32rem)}.mark{display:grid;place-items:center;width:3rem;height:3rem;border-radius:.7rem;color:var(--color-primary);background:#ededff;font-weight:750}.logo{max-width:11rem;height:3.5rem;object-fit:contain}`]
})
export class Maintenance {
  readonly settings = inject(SettingsService); private readonly router = inject(Router);
  retry() { this.router.navigateByUrl('/dashboard'); }
}

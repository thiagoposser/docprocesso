import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Header } from '../header/header';
import { Sidebar } from '../sidebar/sidebar';

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet, Header, Sidebar],
  template: `
    <div class="admin-shell" [class.sidebar-collapsed]="sidebarCollapsed()">
      <app-sidebar [collapsed]="sidebarCollapsed()" [mobileOpen]="mobileOpen()" (navigate)="mobileOpen.set(false)" />
      @if (mobileOpen()) { <button class="sidebar-backdrop" aria-label="Fechar menu" (click)="mobileOpen.set(false)"></button> }
      <div class="admin-main">
        <app-header (toggleDesktop)="sidebarCollapsed.update(value => !value)" (toggleMobile)="mobileOpen.update(value => !value)" />
        <main class="admin-content"><div class="container-fluid px-3 px-lg-4 py-4"><router-outlet /></div></main>
      </div>
    </div>
  `,
  styleUrl: './main-layout.scss'
})
export class MainLayout {
  readonly sidebarCollapsed = signal(false);
  readonly mobileOpen = signal(false);
}

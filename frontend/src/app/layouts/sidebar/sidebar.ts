import { Component, input, output, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { APPLICATION_CONFIG } from '../../core/config/application.config';
import { AppIcon } from '../../shared/components/app-icon/app-icon';
import { AuthService } from '../../core/auth/auth.service';
import { inject } from '@angular/core';
import { SettingsService } from '../../features/settings/services/settings.service';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, AppIcon],
  template: `
    <aside class="sidebar" [class.collapsed]="collapsed()" [class.mobile-open]="mobileOpen()" aria-label="Menu principal">
      <a class="sidebar-brand" routerLink="/dashboard" (click)="navigate.emit()">
        @if (settings.logoUrl()) { <img class="brand-logo" [src]="settings.logoUrl()" alt=""> } @else { <span class="brand-mark">{{ settings.shortName() }}</span> }<span class="brand-name">{{ settings.name() }}</span>
      </a>
      <nav class="sidebar-nav">
        <a routerLink="/dashboard" routerLinkActive="active" title="Dashboard" (click)="navigate.emit()"><span class="nav-icon"><app-icon name="dashboard" /></span><span class="nav-label">Dashboard</span></a>
        <a routerLink="/documentos" routerLinkActive="active" title="Documentos" (click)="navigate.emit()"><span class="nav-icon"><app-icon name="document" /></span><span class="nav-label">Documentos</span></a>
        @if (auth.isAdmin() || canViewAudit() || canManageSectors()) {
          <button type="button" class="submenu-toggle" [class.active]="adminOpen()" (click)="adminOpen.update(value => !value)" [attr.aria-expanded]="adminOpen()">
            <span class="nav-icon"><app-icon name="settings" /></span><span class="nav-label">Administração</span><span class="submenu-arrow"><app-icon name="arrow" [size]="14" /></span>
          </button>
          @if (adminOpen() && !collapsed()) {
            <div class="submenu">@if (auth.isAdmin()) { <a routerLink="/administracao/usuarios" routerLinkActive="active" (click)="navigate.emit()">Usuários</a><a routerLink="/configuracoes" routerLinkActive="active" (click)="navigate.emit()">Configurações</a> } @if (canManageSectors()) { <a routerLink="/administracao/setores" routerLinkActive="active" (click)="navigate.emit()">Setores</a> } @if (canViewAudit()) { <a routerLink="/administracao/auditoria" routerLinkActive="active" (click)="navigate.emit()">Auditoria</a> }</div>
          }
        }
        <a routerLink="/perfil" routerLinkActive="active" title="Perfil" (click)="navigate.emit()"><span class="nav-icon"><app-icon name="user" /></span><span class="nav-label">Perfil</span></a>
      </nav>
      <div class="sidebar-footer"><span class="nav-label">{{ config.environment }}</span></div>
    </aside>
  `,
  styleUrl: './sidebar.scss'
})
export class Sidebar {
  readonly collapsed = input(false);
  readonly mobileOpen = input(false);
  readonly navigate = output<void>();
  readonly adminOpen = signal(true);
  readonly config = APPLICATION_CONFIG;
  readonly auth = inject(AuthService);
  readonly settings = inject(SettingsService);
  readonly canViewAudit = () => Boolean(this.auth.user()?.permissions.includes('audit.view_auditlog'));
  readonly canManageSectors = () => Boolean(this.auth.user()?.is_staff || this.auth.user()?.permissions.includes('sectors.manage_sector'));
}

import { DatePipe } from '@angular/common';
import { Component, computed, inject, output, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs';
import { APPLICATION_CONFIG } from '../../core/config/application.config';
import { AppIcon } from '../../shared/components/app-icon/app-icon';
import { AuthService } from '../../core/auth/auth.service';
import { SettingsService } from '../../features/settings/services/settings.service';
import { NotificationService } from '../../features/notifications/services/notification.service';

@Component({
  selector: 'app-header',
  imports: [RouterLink, DatePipe, AppIcon],
  template: `
    <header class="app-header sticky-top bg-white border-bottom">
      <div class="d-flex align-items-center gap-2 h-100 px-3 px-lg-4">
        <button class="btn btn-light d-none d-lg-inline-flex menu-button" type="button" aria-label="Recolher menu" (click)="toggleDesktop.emit()"><app-icon name="menu" /></button>
        <button class="btn btn-light d-lg-none menu-button" type="button" aria-label="Abrir menu" (click)="toggleMobile.emit()"><app-icon name="menu" /></button>
        <div class="min-w-0 me-auto"><span class="fw-semibold text-truncate d-block">{{ pageTitle() }}</span><small class="text-body-secondary d-none d-sm-block">{{ settings.name() }}</small></div>
        <div class="position-relative"><button class="btn btn-light notification-button" type="button" aria-label="Notificações" [attr.aria-expanded]="notificationMenuOpen()" (click)="toggleNotifications()"><app-icon name="bell" />@if (notifications.unreadCount() > 0) { <span class="notification-count">{{ notifications.unreadCount() > 99 ? '99+' : notifications.unreadCount() }}</span> }</button>@if (notificationMenuOpen()) { <div class="notification-menu dropdown-menu show shadow-sm end-0 mt-2"><div class="d-flex align-items-center justify-content-between px-3 py-2 border-bottom"><strong class="small">Notificações</strong>@if (notifications.unreadCount()) { <button class="btn btn-link btn-sm p-0" type="button" (click)="markAll()">Marcar todas</button> }</div><div class="notification-list">@for (item of notifications.recent(); track item.id) { <button class="notification-item" [class.unread]="!item.read" type="button" (click)="openNotification(item)"><span class="notification-dot"></span><span><strong>{{ item.title }}</strong><small>{{ item.message }}</small><time>{{ item.created_at | date:'short' }}</time></span></button> } @empty { <div class="p-4 text-center text-body-secondary small">Nenhuma notificação.</div> }</div><a class="dropdown-item text-center border-top mt-0 py-2" routerLink="/notificacoes" (click)="notificationMenuOpen.set(false)">Ver todas</a></div> }</div>
        <div class="position-relative">
          <button class="btn btn-light d-flex align-items-center gap-2" type="button" [attr.aria-expanded]="userMenuOpen()" (click)="userMenuOpen.update(value => !value)">
            <span class="user-avatar">{{ initials() }}</span><span class="d-none d-md-block text-start"><span class="d-block small fw-semibold">{{ auth.user()?.name }}</span><span class="d-block text-body-secondary user-role">{{ auth.user()?.groups?.[0] || 'Usuário' }}</span></span><app-icon name="arrow" [size]="13" />
          </button>
          @if (userMenuOpen()) {
            <div class="user-menu dropdown-menu show shadow-sm end-0 mt-2">
              <a class="dropdown-item" routerLink="/perfil" (click)="userMenuOpen.set(false)">Meu perfil</a>
              <div class="dropdown-divider"></div>
              <button class="dropdown-item text-danger" type="button" (click)="logout()">Sair</button>
            </div>
          }
        </div>
      </div>
    </header>
  `,
  styleUrl: './header.scss'
})
export class Header {
  readonly toggleDesktop = output<void>();
  readonly toggleMobile = output<void>();
  readonly userMenuOpen = signal(false);
  readonly notificationMenuOpen = signal(false);
  readonly config = APPLICATION_CONFIG;
  readonly auth = inject(AuthService);
  readonly settings = inject(SettingsService);
  readonly notifications = inject(NotificationService);
  readonly initials = computed(() => (this.auth.user()?.name || 'U').split(' ').slice(0, 2).map(part => part[0]).join(''));
  readonly pageTitle = signal('');
  private readonly router = inject(Router);

  constructor() {
    this.updateTitle();
    this.notifications.refresh().subscribe({error:()=>this.notifications.loading.set(false)});
    this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(() => { this.updateTitle(); this.notifications.refresh().subscribe({error:()=>this.notifications.loading.set(false)}); });
  }

  private updateTitle() {
    let route = this.router.routerState.snapshot.root;
    while (route.firstChild) route = route.firstChild;
    this.pageTitle.set(route.data['breadcrumb'] ?? this.settings.name());
  }
  logout() { this.userMenuOpen.set(false); this.auth.logout().subscribe(); }
  toggleNotifications() { this.userMenuOpen.set(false); this.notificationMenuOpen.update(value=>!value); }
  openNotification(item: import('../../features/notifications/models/notification.models').NotificationItem) { this.notificationMenuOpen.set(false); this.notifications.open(item); }
  markAll() { this.notifications.readAll().subscribe(); }
}

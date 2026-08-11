import { Routes } from '@angular/router';
import { adminGuard, auditGuard, authGuard, sectorGuard } from './core/guards/auth.guard';
import { authResolver } from './core/resolvers/auth.resolver';

export const routes: Routes = [
  { path: 'login', title: 'Login', loadComponent: () => import('./features/auth/login/login').then(m => m.Login) },
  { path: 'manutencao', title: 'Manutenção', loadComponent: () => import('./features/settings/pages/maintenance/maintenance').then(m => m.Maintenance) },
  {
    path: '',
    canActivate: [authGuard],
    resolve: { currentUser: authResolver },
    loadComponent: () => import('./layouts/main-layout/main-layout').then(m => m.MainLayout),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: 'dashboard', title: 'Dashboard', data: { breadcrumb: 'Dashboard' }, loadComponent: () => import('./features/dashboard/dashboard').then(m => m.Dashboard) },
      { path: 'documentos', title: 'Documentos', data: { breadcrumb: 'Documentos' }, loadComponent: () => import('./features/documents/pages/document-list/document-list').then(m => m.DocumentList) },
      { path: 'documentos/novo', title: 'Novo documento', canActivate: [adminGuard], data: { breadcrumb: 'Novo documento' }, loadComponent: () => import('./features/documents/pages/document-form/document-form').then(m => m.DocumentForm) },
      { path: 'documentos/:id/editar', title: 'Editar documento', canActivate: [adminGuard], data: { breadcrumb: 'Editar documento', mode: 'edit' }, loadComponent: () => import('./features/documents/pages/document-form/document-form').then(m => m.DocumentForm) },
      { path: 'documentos/:id', title: 'Detalhes do documento', data: { breadcrumb: 'Detalhes do documento' }, loadComponent: () => import('./features/documents/pages/document-detail/document-detail').then(m => m.DocumentDetail) },
      {
        path: 'administracao', data: { breadcrumb: 'Administração' }, children: [
          { path: '', pathMatch: 'full', redirectTo: 'usuarios' },
          { path: 'usuarios', title: 'Usuários', canActivate: [adminGuard], data: { breadcrumb: 'Usuários' }, loadComponent: () => import('./features/administration/users/user-list/user-list').then(m => m.UserList) },
          { path: 'usuarios/novo', title: 'Novo usuário', canActivate: [adminGuard], data: { breadcrumb: 'Novo usuário' }, loadComponent: () => import('./features/administration/users/user-form/user-form').then(m => m.UserForm) },
          { path: 'usuarios/:id/editar', title: 'Editar usuário', canActivate: [adminGuard], data: { breadcrumb: 'Editar usuário', mode: 'edit' }, loadComponent: () => import('./features/administration/users/user-form/user-form').then(m => m.UserForm) },
          { path: 'usuarios/:id', title: 'Detalhes do usuário', canActivate: [adminGuard], data: { breadcrumb: 'Detalhes', mode: 'view' }, loadComponent: () => import('./features/administration/users/user-form/user-form').then(m => m.UserForm) },
          { path: 'setores', title: 'Setores', canActivate: [sectorGuard], data: { breadcrumb: 'Setores' }, loadComponent: () => import('./features/sectors/pages/sector-list/sector-list').then(m => m.SectorList) },
          { path: 'setores/novo', title: 'Novo setor', canActivate: [sectorGuard], data: { breadcrumb: 'Novo setor' }, loadComponent: () => import('./features/sectors/pages/sector-form/sector-form').then(m => m.SectorForm) },
          { path: 'setores/:id/editar', title: 'Editar setor', canActivate: [sectorGuard], data: { breadcrumb: 'Editar setor' }, loadComponent: () => import('./features/sectors/pages/sector-form/sector-form').then(m => m.SectorForm) },
          { path: 'auditoria', title: 'Auditoria', canActivate: [auditGuard], data: { breadcrumb: 'Auditoria' }, loadComponent: () => import('./features/administration/audit/pages/audit-list/audit-list').then(m => m.AuditList) },
          { path: 'auditoria/:id', title: 'Detalhes da auditoria', canActivate: [auditGuard], data: { breadcrumb: 'Detalhes da auditoria' }, loadComponent: () => import('./features/administration/audit/pages/audit-detail/audit-detail').then(m => m.AuditDetail) }
        ]
      },
      { path: 'configuracoes', title: 'Configurações', canActivate: [adminGuard], data: { breadcrumb: 'Configurações' }, loadComponent: () => import('./features/settings/pages/settings-form/settings-form').then(m => m.SettingsForm) },
      { path: 'perfil', title: 'Perfil', data: { breadcrumb: 'Perfil' }, loadComponent: () => import('./features/profile/profile').then(m => m.Profile) },
      { path: 'notificacoes', title: 'Notificações', data: { breadcrumb: 'Notificações' }, loadComponent: () => import('./features/notifications/pages/notification-list/notification-list').then(m => m.NotificationList) }
    ]
  },
  { path: '403', title: 'Acesso negado', data: { code: 403, heading: 'Acesso negado' }, loadComponent: () => import('./features/errors/error-page').then(m => m.ErrorPage) },
  { path: '404', title: 'Página não encontrada', data: { code: 404, heading: 'Página não encontrada' }, loadComponent: () => import('./features/errors/error-page').then(m => m.ErrorPage) },
  { path: '**', redirectTo: '404' }
];

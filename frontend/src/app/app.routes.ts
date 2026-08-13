import { Routes } from '@angular/router';
import { adminGuard, auditGuard, authGuard, organizationalFunctionGuard, paymentAddGuard, paymentChangeGuard, paymentViewGuard, processAddGuard, processChangeGuard, processViewGuard, reportsGuard, sectorGuard, unitGuard, workflowGuard } from './core/guards/auth.guard';
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
      { path: 'relatorios', title: 'Relatórios', canActivate: [reportsGuard], data: { breadcrumb: 'Relatórios' }, loadComponent: () => import('./features/reports/pages/report-dashboard/report-dashboard').then(m => m.ReportDashboard) },
      { path: 'processos', title: 'Processos', canActivate: [processViewGuard], data: { breadcrumb: 'Processos' }, loadComponent: () => import('./features/processes/pages/process-list/process-list').then(m => m.ProcessList) },
      { path: 'processos/novo', title: 'Novo processo', canActivate: [processAddGuard], data: { breadcrumb: 'Novo processo' }, loadComponent: () => import('./features/processes/pages/process-form/process-form').then(m => m.ProcessForm) },
      { path: 'processos/:id/editar', title: 'Editar processo', canActivate: [processChangeGuard], data: { breadcrumb: 'Editar processo' }, loadComponent: () => import('./features/processes/pages/process-form/process-form').then(m => m.ProcessForm) },
      { path: 'processos/:id', title: 'Detalhes do processo', canActivate: [processViewGuard], data: { breadcrumb: 'Detalhes do processo' }, loadComponent: () => import('./features/processes/pages/process-detail/process-detail').then(m => m.ProcessDetail) },
      { path: 'pagamentos', title: 'Pagamentos', canActivate: [paymentViewGuard], data: { breadcrumb: 'Pagamentos' }, loadComponent: () => import('./features/payments/pages/payment-list/payment-list').then(m => m.PaymentList) },
      { path: 'pagamentos/novo', title: 'Novo pagamento', canActivate: [paymentViewGuard, paymentAddGuard], data: { breadcrumb: 'Novo pagamento' }, loadComponent: () => import('./features/payments/pages/payment-form/payment-form').then(m => m.PaymentForm) },
      { path: 'pagamentos/:id/editar', title: 'Editar pagamento', canActivate: [paymentViewGuard, paymentChangeGuard], data: { breadcrumb: 'Editar pagamento' }, loadComponent: () => import('./features/payments/pages/payment-form/payment-form').then(m => m.PaymentForm) },
      { path: 'pagamentos/:id', title: 'Detalhes do pagamento', canActivate: [paymentViewGuard], data: { breadcrumb: 'Detalhes do pagamento' }, loadComponent: () => import('./features/payments/pages/payment-detail/payment-detail').then(m => m.PaymentDetail) },
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
          { path: 'estrutura', pathMatch: 'full', redirectTo: 'estrutura/unidades' },
          { path: 'estrutura/unidades', title: 'Unidades', canActivate: [unitGuard], data: { breadcrumb: 'Unidades' }, loadComponent: () => import('./features/sectors/pages/unit-list/unit-list').then(m => m.UnitList) },
          { path: 'estrutura/unidades/nova', title: 'Nova unidade', canActivate: [unitGuard], data: { breadcrumb: 'Nova unidade' }, loadComponent: () => import('./features/sectors/pages/unit-form/unit-form').then(m => m.UnitForm) },
          { path: 'estrutura/unidades/:id/editar', title: 'Editar unidade', canActivate: [unitGuard], data: { breadcrumb: 'Editar unidade' }, loadComponent: () => import('./features/sectors/pages/unit-form/unit-form').then(m => m.UnitForm) },
          { path: 'estrutura/setores', title: 'Setores', canActivate: [sectorGuard], data: { breadcrumb: 'Setores' }, loadComponent: () => import('./features/sectors/pages/sector-list/sector-list').then(m => m.SectorList) },
          { path: 'estrutura/setores/novo', title: 'Novo setor', canActivate: [sectorGuard], data: { breadcrumb: 'Novo setor' }, loadComponent: () => import('./features/sectors/pages/sector-form/sector-form').then(m => m.SectorForm) },
          { path: 'estrutura/setores/:id/editar', title: 'Editar setor', canActivate: [sectorGuard], data: { breadcrumb: 'Editar setor' }, loadComponent: () => import('./features/sectors/pages/sector-form/sector-form').then(m => m.SectorForm) },
          { path: 'estrutura/funcoes', title: 'Funções', canActivate: [organizationalFunctionGuard], data: { breadcrumb: 'Funções' }, loadComponent: () => import('./features/sectors/pages/function-list/function-list').then(m => m.FunctionList) },
          { path: 'estrutura/funcoes/nova', title: 'Nova função', canActivate: [organizationalFunctionGuard], data: { breadcrumb: 'Nova função' }, loadComponent: () => import('./features/sectors/pages/function-form/function-form').then(m => m.FunctionForm) },
          { path: 'estrutura/funcoes/:id/editar', title: 'Editar função', canActivate: [organizationalFunctionGuard], data: { breadcrumb: 'Editar função' }, loadComponent: () => import('./features/sectors/pages/function-form/function-form').then(m => m.FunctionForm) },
          { path: 'estrutura/vinculos', title: 'Vínculos organizacionais', canActivate: [adminGuard], data: { breadcrumb: 'Vínculos' }, loadComponent: () => import('./features/administration/users/user-list/user-list').then(m => m.UserList) },
          { path: 'fluxos', title: 'Fluxos administrativos', canActivate: [workflowGuard], data: { breadcrumb: 'Fluxos' }, loadComponent: () => import('./features/administration/workflows/workflow-admin').then(m => m.WorkflowAdmin) },
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

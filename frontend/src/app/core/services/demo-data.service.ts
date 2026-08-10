import { Injectable } from '@angular/core';
import { DocumentItem } from '../models/application.models';

@Injectable({ providedIn: 'root' })
export class DemoDataService {
  readonly documents: DocumentItem[] = [
    { id: 1, name: 'Manual de integração', description: 'Orientações para integração de novos usuários.', category: 'Manual', updatedAt: '08/08/2026' },
    { id: 2, name: 'Política de segurança', description: 'Diretrizes de acesso e proteção de dados.', category: 'Política', updatedAt: '04/08/2026' },
    { id: 3, name: 'Relatório mensal', description: 'Resumo operacional do último período.', category: 'Relatório', updatedAt: '01/08/2026' },
    { id: 4, name: 'Modelo de solicitação', description: 'Formulário padrão para novas demandas.', category: 'Modelo', updatedAt: '28/07/2026' }
  ];
}

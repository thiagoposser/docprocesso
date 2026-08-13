import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Page, Workflow, WorkflowStage, WorkflowTransition } from './workflow.models';

@Injectable({providedIn:'root'})
export class WorkflowService {
  private readonly http=inject(HttpClient);
  workflows(){return this.http.get<Page<Workflow>>('/api/workflows/');}
  createWorkflow(payload:unknown){return this.http.post<Workflow>('/api/workflows/',payload);}
  updateWorkflow(id:number,payload:unknown){return this.http.patch<Workflow>(`/api/workflows/${id}/`,payload);}
  stages(workflow:number){return this.http.get<Page<WorkflowStage>>('/api/workflow-stages/',{params:{workflow}});}
  createStage(payload:unknown){return this.http.post<WorkflowStage>('/api/workflow-stages/',payload);}
  transitions(workflow:number){return this.http.get<Page<WorkflowTransition>>('/api/workflow-transitions/',{params:{workflow}});}
  createTransition(payload:unknown){return this.http.post<WorkflowTransition>('/api/workflow-transitions/',payload);}
  updateTransition(id:number,payload:unknown){return this.http.patch<WorkflowTransition>(`/api/workflow-transitions/${id}/`,payload);}
}

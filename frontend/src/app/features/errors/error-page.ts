import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

@Component({
  selector: 'app-error-page',
  imports: [RouterLink],
  template: `
    <main class="error">
      <section>
        <strong>{{ route.snapshot.data['code'] }}</strong>
        <h1>{{ route.snapshot.data['heading'] }}</h1>
        <a routerLink="/dashboard">Voltar ao dashboard</a>
      </section>
    </main>
  `,
  styles: [`
    .error { min-height: 100vh; display: grid; place-items: center; text-align: center; }
    strong { color: #2563eb; font-size: 5rem; }
    h1 { margin: 0 0 1rem; color: #0f172a; }
    a { color: #2563eb; }
  `]
})
export class ErrorPage {
  protected readonly route = inject(ActivatedRoute);
}

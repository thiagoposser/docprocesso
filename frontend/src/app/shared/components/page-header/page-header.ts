import { Component, input } from '@angular/core';

@Component({
  selector: 'app-page-header',
  template: `
    <div class="d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-3 mb-4 page-heading">
      <div><h1 class="mb-1">{{ title() }}</h1><p class="text-body-secondary mb-0">{{ description() }}</p></div>
      <ng-content />
    </div>
  `,
  styles: [`.page-heading h1 { font-size: 1.55rem; line-height: 1.25; } .page-heading p { font-size: .875rem; }`]
})
export class PageHeader {
  readonly title = input.required<string>();
  readonly description = input('');
}

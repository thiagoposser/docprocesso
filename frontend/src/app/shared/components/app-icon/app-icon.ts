import { Component, computed, input } from '@angular/core';

type IconName = 'dashboard' | 'document' | 'settings' | 'user' | 'menu' | 'check' | 'plus' | 'arrow' | 'bell';

const paths: Record<IconName, string> = {
  dashboard: 'M3 3h7v7H3V3Zm11 0h7v4h-7V3ZM3 14h7v7H3v-7Zm11-3h7v10h-7V11Z',
  document: 'M6 2h8l4 4v16H6V2Zm8 1.5V7h3.5M9 11h6M9 15h6M9 19h4',
  settings: 'M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Zm8 3.5 2-1-2-3-2.2.4-1.2-1.2.4-2.2-3-2-1 2-2-1-3 2 .4 2.2-1.2 1.2L6 8l-2.2-.4-2 3 2 1v2l-2 1 2 3L6 17l1.2 1.2-.4 2.2 3 2 1-2h2l1 2 3-2-.4-2.2L17.6 17l2.2.4 2-3-2-1v-2Z',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9a7 7 0 0 1 14 0',
  menu: 'M4 7h16M4 12h16M4 17h16',
  check: 'm5 12 4 4L19 6',
  plus: 'M12 5v14M5 12h14',
  arrow: 'm9 6 6 6-6 6',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4'
};

@Component({
  selector: 'app-icon',
  template: `<svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path [attr.d]="path()" /></svg>`,
  styles: [':host { display: inline-flex; line-height: 0; }']
})
export class AppIcon {
  readonly name = input.required<IconName>();
  readonly size = input(18);
  readonly path = computed(() => paths[this.name()]);
}

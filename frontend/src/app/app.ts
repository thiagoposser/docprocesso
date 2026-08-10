import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SettingsService } from './features/settings/services/settings.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  private readonly settings = inject(SettingsService);
  constructor() { this.settings.loadPublic().subscribe({ error: () => undefined }); }
}

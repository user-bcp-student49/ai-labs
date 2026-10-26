import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, NgZone, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthUser } from '../models/auth.models';
import { Task } from '../models/task.models';
import { SessionService } from '../services/session.service';
import { TasksService } from '../services/tasks.service';
import { getErrorMessage } from '../utils/error-message';
import { formatTaskLabel } from '../utils/legacy-format';

const STATUS_LABELS: Record<string, string> = {
  TODO: 'Por hacer',
  IN_PROGRESS: 'En progreso',
  DONE: 'Completado',
  RESUELTO: 'Resuelto',
  COMPLETED: 'Completado'
};

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
  tasks: Task[] = [];
  visibleTasks: Task[] = [];
  user: AuthUser | null = null;
  loading = true;
  error = '';

  constructor(
    private router: Router,
    private cdr: ChangeDetectorRef,
    private zone: NgZone,
    private sessionService: SessionService,
    private tasksService: TasksService
  ) {}

  statusLabel(status: string | undefined): string {
    return STATUS_LABELS[(status || '').toUpperCase()] || status || '';
  }

  async ngOnInit(): Promise<void> {
    const token = this.sessionService.getToken();
    if (!token) {
      await this.router.navigate(['/login']);
      return;
    }

    try {
      this.user = this.sessionService.getUser();
      const tasks = await this.tasksService.getTasks(this.user?.username || '', token);
      this.tasks = tasks;
      this.visibleTasks = this.createVisibleTasks(tasks);
      this.zone.run(() => {
        this.loading = false;
        this.cdr.detectChanges();
      });
    } catch (error: unknown) {
      this.zone.run(() => {
        this.error = getErrorMessage(error, 'No se pudo cargar el dashboard');
        this.loading = false;
        this.cdr.detectChanges();
      });
    }
  }

  private createVisibleTasks(tasks: Task[]): Task[] {
    return tasks
      .filter((task) => task.status !== 'ARCHIVED')
      .map((task) => ({ ...task, label: formatTaskLabel(task) }))
      .sort((first, second) => first.priority !== undefined && second.priority !== undefined
        && first.priority > second.priority ? -1 : 1);
  }

  async logout(): Promise<void> {
    this.sessionService.clearSession();
    await this.router.navigate(['/login']);
  }
}

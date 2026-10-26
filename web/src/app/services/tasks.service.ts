import { Injectable } from '@angular/core';
import axios from 'axios';
import { Task } from '../models/task.models';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class TasksService {
  async getTasks(owner: string, token: string): Promise<Task[]> {
    const url = new URL('/api/tasks', environment.tasksApiUrl);
    url.searchParams.set('owner', owner);
    const response = await axios.get<Task[]>(url.toString(), {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  }
}

import '@angular/compiler';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import { TasksService } from './tasks.service';

vi.mock('axios', () => ({
  default: {
    get: vi.fn()
  }
}));

describe('TasksService', () => {
  let service: TasksService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new TasksService();
  });

  it('requests tasks with an encoded owner and bearer token', async () => {
    const tasks = [{ id: 1, title: 'Example' }];
    vi.mocked(axios.get).mockResolvedValue({ data: tasks } as never);

    await expect(service.getTasks("student' test", 'fake-token')).resolves.toEqual(tasks);
    expect(axios.get).toHaveBeenCalledWith(
      'http://localhost:8000/api/tasks?owner=student%27+test',
      { headers: { Authorization: 'Bearer fake-token' } }
    );
  });
});

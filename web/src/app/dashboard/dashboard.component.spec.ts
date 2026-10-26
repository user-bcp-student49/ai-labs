import '@angular/compiler';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import { DashboardComponent } from './dashboard.component';

describe('DashboardComponent characterization', () => {
  const router = { navigate: vi.fn().mockResolvedValue(true) };
  const changeDetector = { detectChanges: vi.fn() };
  const zone = { run: (callback: () => void) => callback() };
  const sessionService = { getToken: vi.fn(), getUser: vi.fn(), clearSession: vi.fn() };
  const tasksService = { getTasks: vi.fn() };
  let component: DashboardComponent;

  beforeEach(() => {
    vi.clearAllMocks();
    sessionService.getToken.mockReturnValue(null);
    sessionService.getUser.mockReturnValue(null);
    component = new DashboardComponent(
      router as never,
      changeDetector as never,
      zone as never,
      sessionService as never,
      tasksService as never
    );
  });

  it('redirects to login when no token exists', async () => {
    await component.ngOnInit();

    expect(router.navigate).toHaveBeenCalledWith(['/login']);
    expect(tasksService.getTasks).not.toHaveBeenCalled();
  });

  it('requests and displays non-archived tasks in descending priority order', async () => {
    sessionService.getToken.mockReturnValue('fake-token');
    sessionService.getUser.mockReturnValue({ username: 'student' });
    tasksService.getTasks.mockResolvedValue([
      { title: 'Low', priority: 1, owner: 'student', status: 'TODO' },
      { title: 'High', priority: 3, owner: 'student', status: 'DONE' },
      { title: 'Archived', priority: 5, owner: 'student', status: 'ARCHIVED' }
    ]);

    await component.ngOnInit();

    expect(tasksService.getTasks).toHaveBeenCalledWith('student', 'fake-token');
    expect(component.visibleTasks.map((task) => task.title)).toEqual(['High', 'Low']);
    expect(component.visibleTasks[0].label).toBe('3 · STUDENT');
    expect(component.loading).toBe(false);
    expect(changeDetector.detectChanges).toHaveBeenCalled();
  });

  it('shows a task service error and ends loading', async () => {
    sessionService.getToken.mockReturnValue('fake-token');
    sessionService.getUser.mockReturnValue({ username: 'student' });
    tasksService.getTasks.mockRejectedValue(new Error('network unavailable'));

    await component.ngOnInit();

    expect(component.error).toBe('network unavailable');
    expect(component.loading).toBe(false);
  });

  it('shows an invalid-token response without clearing the session or redirecting', async () => {
    const unauthorizedError = new axios.AxiosError('Request failed with status code 401');
    unauthorizedError.response = {
      data: { detail: 'Not authorized' },
      status: 401,
      statusText: 'Unauthorized',
      headers: {},
      config: { headers: new axios.AxiosHeaders() }
    };
    sessionService.getToken.mockReturnValue('invalid-token');
    sessionService.getUser.mockReturnValue({ username: 'student' });
    tasksService.getTasks.mockRejectedValue(unauthorizedError);

    await component.ngOnInit();

    expect(component.error).toBe('Not authorized');
    expect(component.loading).toBe(false);
    expect(sessionService.clearSession).not.toHaveBeenCalled();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('shows a task timeout error and ends loading', async () => {
    sessionService.getToken.mockReturnValue('fake-token');
    sessionService.getUser.mockReturnValue({ username: 'student' });
    tasksService.getTasks.mockRejectedValue(new Error('timeout of 1000ms exceeded'));

    await component.ngOnInit();

    expect(component.error).toBe('timeout of 1000ms exceeded');
    expect(component.loading).toBe(false);
  });

  it('reports an unexpected non-array task response', async () => {
    sessionService.getToken.mockReturnValue('fake-token');
    sessionService.getUser.mockReturnValue({ username: 'student' });
    tasksService.getTasks.mockResolvedValue({ tasks: [] });

    await component.ngOnInit();

    expect(component.error).toContain('filter');
    expect(component.loading).toBe(false);
  });

  it('clears session credentials and navigates to login on logout', async () => {
    await component.logout();

    expect(sessionService.clearSession).toHaveBeenCalled();
    expect(router.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('completes the login-to-task-list happy path', async () => {
    const loginRouter = { navigate: vi.fn().mockResolvedValue(true) };
    const loginAuthService = {
      login: vi.fn().mockResolvedValue({
        token: 'fake-token',
        user: { username: 'student' }
      })
    };
    const loggedInSession = {
      getPreferences: vi.fn().mockReturnValue(null),
      saveSession: vi.fn(),
      savePreferences: vi.fn(),
      getToken: vi.fn().mockReturnValue('fake-token'),
      getUser: vi.fn().mockReturnValue({ username: 'student' }),
      clearSession: vi.fn()
    };
    const taskService = {
      getTasks: vi.fn().mockResolvedValue([
        { id: 1, title: 'Review login', status: 'TODO', priority: 2, owner: 'student' }
      ])
    };
    const { LoginComponent } = await import('../login/login.component');
    const login = new LoginComponent(
      loginRouter as never,
      loginAuthService as never,
      loggedInSession as never
    );
    login.username = 'student';
    login.password = 'Workshop123!';

    await login.login();

    const dashboard = new DashboardComponent(
      router as never,
      changeDetector as never,
      zone as never,
      loggedInSession as never,
      taskService as never
    );
    await dashboard.ngOnInit();

    expect(loginRouter.navigate).toHaveBeenCalledWith(['/dashboard']);
    expect(loggedInSession.saveSession).toHaveBeenCalledWith({
      token: 'fake-token',
      user: { username: 'student' }
    });
    expect(taskService.getTasks).toHaveBeenCalledWith('student', 'fake-token');
    expect(dashboard.visibleTasks.map((task) => task.title)).toEqual(['Review login']);
    expect(dashboard.loading).toBe(false);
    expect(dashboard.error).toBe('');
  });
});

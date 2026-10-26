export type TaskPriority = number | string;

export interface Task {
  id?: number | string;
  title?: string;
  description?: string;
  status?: string;
  priority?: TaskPriority;
  owner?: string;
  label?: string;
}

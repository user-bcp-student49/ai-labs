import { describe, expect, it } from 'vitest';
import { formatTaskLabel } from './legacy-format';

describe('formatTaskLabel', () => {
  it('formats priority and owner', () => {
    expect(formatTaskLabel({ priority: 'high', owner: 'student' })).toBe('HIGH · STUDENT');
  });

  it('keeps the existing defaults for missing values and empty tasks', () => {
    expect(formatTaskLabel({ priority: 0, owner: '' })).toBe('NORMAL · SIN-ASIGNAR');
    expect(formatTaskLabel(null)).toBe('SIN-DATOS');
  });
});

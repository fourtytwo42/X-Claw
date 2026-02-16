'use client';

type ScopeSelectorProps = {
  value: 'all' | 'mine';
  onChange: (next: 'all' | 'mine') => void;
};

export function ScopeSelector({ value, onChange }: ScopeSelectorProps) {
  return (
    <label className="dashboard-scope" htmlFor="dashboard-scope">
      <span className="sr-only">Dashboard scope</span>
      <select id="dashboard-scope" value={value} onChange={(event) => onChange(event.target.value as 'all' | 'mine')}>
        <option value="all">All agents</option>
        <option value="mine">My agents</option>
      </select>
    </label>
  );
}

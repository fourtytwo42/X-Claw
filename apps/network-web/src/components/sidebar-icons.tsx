import type { SVGProps } from 'react';

type SidebarIconName = 'dashboard' | 'explore' | 'approvals' | 'settings' | 'status' | 'howto';

type SidebarIconProps = {
  name: SidebarIconName;
  className?: string;
};

export function SidebarIcon({ name, className }: SidebarIconProps) {
  const common: SVGProps<SVGSVGElement> = {
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.9,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
    className
  };

  if (name === 'dashboard') {
    return (
      <svg {...common}>
        <rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.5" />
        <rect x="13" y="3.5" width="7.5" height="5.2" rx="1.5" />
        <rect x="13" y="10.8" width="7.5" height="9.7" rx="1.5" />
        <rect x="3.5" y="13" width="7.5" height="7.5" rx="1.5" />
      </svg>
    );
  }

  if (name === 'explore') {
    return (
      <svg {...common}>
        <path d="M4.5 8.8a2.8 2.8 0 0 1 2.8-2.8h9.4a2.8 2.8 0 0 1 2.8 2.8v7.6a2.8 2.8 0 0 1-2.8 2.8H7.3a2.8 2.8 0 0 1-2.8-2.8Z" />
        <path d="M8.2 10.2h7.6" />
        <path d="M8.2 13.2h7.6" />
        <path d="M10 16h4" />
        <path d="M8.7 6V4.3" />
        <path d="M15.3 6V4.3" />
      </svg>
    );
  }

  if (name === 'approvals') {
    return (
      <svg {...common}>
        <path d="M12 2.8 4.4 6.2v5.1c0 4.4 2.9 8.4 7.6 9.9 4.7-1.5 7.6-5.5 7.6-9.9V6.2Z" />
        <path d="m8.7 12.1 2.2 2.2 4.4-4.6" />
      </svg>
    );
  }

  if (name === 'settings') {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="2.8" />
        <path d="M19.4 12a7.4 7.4 0 0 0-.1-1.2l2-1.6-2-3.5-2.5 1a7.8 7.8 0 0 0-2-1.2l-.4-2.7h-4l-.4 2.7a7.8 7.8 0 0 0-2 1.2l-2.5-1-2 3.5 2 1.6a7.4 7.4 0 0 0-.1 2.4l-2 1.6 2 3.5 2.5-1c.6.5 1.3.9 2 1.2l.4 2.7h4l.4-2.7c.7-.3 1.4-.7 2-1.2l2.5 1 2-3.5-2-1.6c.1-.4.1-.8.1-1.2Z" />
      </svg>
    );
  }

  if (name === 'howto') {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="8.8" />
        <path d="M12 10.2v5.2" />
        <circle cx="12" cy="7.3" r="0.35" fill="currentColor" stroke="none" />
      </svg>
    );
  }

  return (
    <svg {...common}>
      <path d="M12 3.2a8.8 8.8 0 1 0 8.8 8.8A8.8 8.8 0 0 0 12 3.2Z" />
      <path d="M12 7.6v4.8" />
      <circle cx="12" cy="16.2" r="0.3" fill="currentColor" stroke="none" />
    </svg>
  );
}

interface EPatrolLogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const sizes = {
  sm: { icon: 32, text: 'text-lg' },
  md: { icon: 40, text: 'text-xl' },
  lg: { icon: 52, text: 'text-2xl' },
}

export function EPatrolLogo({ className = '', size = 'md' }: EPatrolLogoProps) {
  const dim = sizes[size].icon
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg
        width={dim}
        height={dim}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <rect width="64" height="64" rx="14" fill="#0ea5e9" />
        <path
          d="M32 12L48 20V34C48 44 40.5 51.5 32 54C23.5 51.5 16 44 16 34V20L32 12Z"
          fill="#e0f2fe"
          stroke="#0369a1"
          strokeWidth="1.5"
        />
        <circle cx="32" cy="30" r="6" fill="#0369a1" />
        <path
          d="M32 24C28 24 25 27 25 31"
          stroke="#7dd3fc"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path d="M22 38H42" stroke="#0369a1" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <div className="leading-tight">
        <span className={`font-bold tracking-tight text-sky-700 ${sizes[size].text}`}>
          E-PATROL
        </span>
        <p className="text-xs font-medium text-slate-500">Electronic Patrolling</p>
      </div>
    </div>
  )
}

import Image from 'next/image'

interface ShaktiLogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const sizes = {
  sm: { img: 36, text: 'text-lg' },
  md: { img: 44, text: 'text-xl' },
  lg: { img: 64, text: 'text-2xl' },
}

export function EPatrolLogo({ className = '', size = 'md' }: ShaktiLogoProps) {
  const dim = sizes[size].img
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <Image
        src="/logo.png"
        alt="शक्ति - Shakti (The Third Eye)"
        width={dim}
        height={dim}
        className="rounded-lg"
        priority
      />
      <div className="leading-tight">
        <span className={`font-bold tracking-tight text-sky-700 ${sizes[size].text}`}>
          शक्ति - Shakti
        </span>
        <p className="text-xs font-medium text-slate-500">The Third Eye</p>
      </div>
    </div>
  )
}

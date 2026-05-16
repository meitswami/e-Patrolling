'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ComingSoon } from '@/components/ComingSoon'
import { isAuthenticated } from '@/lib/auth'
export default function Page() {
  const router = useRouter()
  useEffect(() => { if (!isAuthenticated()) router.replace('/login') }, [router])
  return <ComingSoon title="Analytics" />
}

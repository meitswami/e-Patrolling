'use client'

import Link from 'next/link'
import { EPatrolLogo } from '@/components/branding/EPatrolLogo'
import { SafetyRequestForm } from '@/components/marketing/SafetyRequestForm'
import { Eye, FileSearch, MapPin, ShieldCheck } from 'lucide-react'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-50 via-white to-slate-50 text-slate-800">
      <header className="sticky top-0 z-20 border-b border-sky-100/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <EPatrolLogo size="sm" />
          <nav className="hidden gap-6 text-sm font-medium text-slate-600 sm:flex">
            <a href="#about" className="hover:text-sky-700">
              What we do
            </a>
            <a href="#safe" className="hover:text-sky-700">
              Want to be Safe
            </a>
            <a href="#support" className="hover:text-sky-700">
              Support
            </a>
            <a href="#contact" className="hover:text-sky-700">
              Contact
            </a>
          </nav>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-5xl px-4 py-16 text-center md:py-24">
          <EPatrolLogo size="lg" className="mx-auto justify-center" />
          <h1 className="mt-8 text-4xl font-bold tracking-tight text-sky-900 md:text-5xl">
            शक्ति - Shakti (The Third Eye)
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600">
            AI-Powered Social Media Intelligence & Women Safety Platform — we monitor abusive
            comments, trolls, and offenders so you stay informed and protected.
          </p>
          <a
            href="#safe"
            className="mt-8 inline-block rounded-xl bg-sky-600 px-8 py-3 text-sm font-semibold text-white shadow-md hover:bg-sky-700"
          >
            Want to be Safe
          </a>
        </section>

        <section id="about" className="border-t border-sky-100 bg-white py-16">
          <div className="mx-auto max-w-5xl px-4">
            <h2 className="text-center text-2xl font-bold text-sky-900">What we do</h2>
            <p className="mx-auto mt-4 max-w-2xl text-center text-slate-600">
              शक्ति - Shakti (The Third Eye) is an AI-Powered Social Media Intelligence &amp; Women Safety
              Platform that helps individuals and communities spot online harassment early — across
              Instagram, Facebook, X, and Threads — with evidence you can act on.
            </p>
            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {[
                {
                  icon: Eye,
                  title: 'Always watching',
                  text: 'We keep an eye on comments and mentions on the profiles you trust us with.',
                },
                {
                  icon: ShieldCheck,
                  title: 'Abuse detection',
                  text: 'AI-assisted detection for slurs, threats, sexual harassment, and bullying.',
                },
                {
                  icon: MapPin,
                  title: 'Regional context',
                  text: 'Hinglish and local language patterns matter — we tune for India-first abuse.',
                },
                {
                  icon: FileSearch,
                  title: 'Evidence ready',
                  text: 'Documented incidents with permalinks for reports and escalation.',
                },
              ].map(({ icon: Icon, title, text }) => (
                <div
                  key={title}
                  className="rounded-xl border border-sky-50 bg-sky-50/50 p-5 text-center"
                >
                  <Icon className="mx-auto h-8 w-8 text-sky-600" />
                  <h3 className="mt-3 font-semibold text-sky-900">{title}</h3>
                  <p className="mt-2 text-sm text-slate-600">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="safe" className="py-16">
          <div className="mx-auto max-w-2xl px-4">
            <SafetyRequestForm />
            <p className="mt-4 text-center text-xs text-slate-500">
              Submissions from this form are stored separately from targets created in the admin
              panel. Our team reviews website requests before enabling monitoring.
            </p>
          </div>
        </section>

        <section id="support" className="border-t border-sky-100 bg-white py-16">
          <div className="mx-auto max-w-3xl px-4">
            <h2 className="text-center text-2xl font-bold text-sky-900">Support</h2>
            <div className="mt-8 space-y-4">
              <details className="rounded-lg border border-slate-200 bg-slate-50/50 px-4 py-3">
                <summary className="cursor-pointer font-medium text-sky-900">
                  Which platforms do you support?
                </summary>
                <p className="mt-2 text-sm text-slate-600">
                  Instagram, Facebook, Twitter/X, and Threads. Add one or more profile links in the
                  form above.
                </p>
              </details>
              <details className="rounded-lg border border-slate-200 bg-slate-50/50 px-4 py-3">
                <summary className="cursor-pointer font-medium text-sky-900">
                  What happens after I submit?
                </summary>
                <p className="mt-2 text-sm text-slate-600">
                  Your request is queued for review. Verified profiles may be added to monitoring
                  after our team confirms details. You are not automatically enrolled in live
                  crawls until reviewed.
                </p>
              </details>
              <details className="rounded-lg border border-slate-200 bg-slate-50/50 px-4 py-3">
                <summary className="cursor-pointer font-medium text-sky-900">
                  Is my data shared publicly?
                </summary>
                <p className="mt-2 text-sm text-slate-600">
                  No. Intake data is used only for safety monitoring and is handled by authorized
                  Shakti operators.
                </p>
              </details>
            </div>
          </div>
        </section>

        <section id="contact" className="py-16">
          <div className="mx-auto max-w-xl px-4 text-center">
            <h2 className="text-2xl font-bold text-sky-900">Contact us</h2>
            <p className="mt-4 text-slate-600">
              Questions about Shakti or your submission? Reach our team at{' '}
              <a
                href="mailto:support@shakti-eye.in"
                className="font-medium text-sky-700 hover:underline"
              >
                support@shakti-eye.in
              </a>
            </p>
          </div>
        </section>
      </main>

      <footer className="border-t border-sky-100 bg-white py-8 text-center text-sm text-slate-500">
        <p>© {new Date().getFullYear()} शक्ति - Shakti (The Third Eye). All rights reserved.</p>
        <p className="mt-2">
          <Link href="/" className="hover:text-sky-700">
            Home
          </Link>
        </p>
      </footer>
    </div>
  )
}

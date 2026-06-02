'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import {
  getFullDictionary,
  addDictionaryTerm,
  removeDictionaryTerm,
  type FullDictionary,
  type LexiconPattern,
  type GlossaryTerm,
  type AddTermPayload,
} from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'

type TabType = 'terms' | 'phrases' | 'patterns' | 'models'

const CATEGORY_COLORS: Record<string, string> = {
  hate_speech: 'text-orange-400 border-orange-500/40 bg-orange-500/10',
  sexual_harassment: 'text-pink-400 border-pink-500/40 bg-pink-500/10',
  rape_threat: 'text-red-400 border-red-500/40 bg-red-500/10',
  threat: 'text-red-300 border-red-400/40 bg-red-400/10',
  stalking: 'text-purple-400 border-purple-500/40 bg-purple-500/10',
  bullying: 'text-amber-400 border-amber-500/40 bg-amber-500/10',
}

export default function DictionaryPage() {
  const router = useRouter()
  const [data, setData] = useState<FullDictionary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('terms')
  const [search, setSearch] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [adding, setAdding] = useState(false)

  // Add form state
  const [newWord, setNewWord] = useState('')
  const [newRegex, setNewRegex] = useState('')
  const [newScore, setNewScore] = useState(0.8)
  const [newLabel, setNewLabel] = useState('hate_speech')
  const [newMeaning, setNewMeaning] = useState('')
  const [newImplication, setNewImplication] = useState('')

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    loadData()
  }, [router])

  async function loadData() {
    try {
      setLoading(true)
      const result = await getFullDictionary()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dictionary')
    } finally {
      setLoading(false)
    }
  }

  async function handleAddTerm() {
    if (!newWord.trim() || !newRegex.trim()) {
      setError('Word and regex pattern are required')
      return
    }
    setAdding(true)
    setError(null)
    setSuccess(null)
    try {
      const payload: AddTermPayload = {
        word: newWord.trim(),
        regex: newRegex.trim(),
        score: newScore,
        label: newLabel,
        meaning_en: newMeaning.trim(),
        offender_implication: newImplication.trim(),
      }
      const result = await addDictionaryTerm(payload)
      setSuccess(result.message)
      setShowAddForm(false)
      setNewWord('')
      setNewRegex('')
      setNewScore(0.8)
      setNewMeaning('')
      setNewImplication('')
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add term')
    } finally {
      setAdding(false)
    }
  }

  async function handleRemoveTerm(id: string) {
    if (!confirm(`Remove "${id}" from the abuse dictionary? This cannot be undone.`)) return
    setError(null)
    setSuccess(null)
    try {
      const result = await removeDictionaryTerm(id)
      setSuccess(result.message)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove term')
    }
  }

  function filterItems<T extends { display?: string; id?: string; regex?: string }>(
    items: T[],
  ): T[] {
    if (!search.trim()) return items
    const q = search.toLowerCase()
    return items.filter(
      (item) =>
        (item.display && item.display.toLowerCase().includes(q)) ||
        (item.id && item.id.toLowerCase().includes(q)) ||
        (item.regex && item.regex.toLowerCase().includes(q)),
    )
  }

  const filteredTerms = data ? filterItems(data.terms) : []
  const filteredPhrases = data ? filterItems(data.phrases) : []
  const filteredPatterns = data
    ? data.patterns.filter(
        (p) =>
          !search.trim() ||
          p.regex.toLowerCase().includes(search.toLowerCase()) ||
          p.label.toLowerCase().includes(search.toLowerCase()),
      )
    : []

  return (
    <AppShell title="Abuse Dictionary" subtitle="Keyword patterns, terms, and ML models used for detection">
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      {success && (
        <p className="mb-4 rounded-lg border border-patrol-accent/30 bg-patrol-accent/10 px-4 py-3 text-sm text-patrol-accent">
          {success}
        </p>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading dictionary…</p>}

      {!loading && data && (
        <>
          {/* Stats bar */}
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg border border-patrol-border bg-patrol-card p-3 text-center">
              <p className="text-2xl font-bold text-patrol-accent">{data.total_patterns}</p>
              <p className="text-xs text-patrol-muted">Detection Patterns</p>
            </div>
            <div className="rounded-lg border border-patrol-border bg-patrol-card p-3 text-center">
              <p className="text-2xl font-bold text-orange-400">{data.total_terms}</p>
              <p className="text-xs text-patrol-muted">Abuse Terms</p>
            </div>
            <div className="rounded-lg border border-patrol-border bg-patrol-card p-3 text-center">
              <p className="text-2xl font-bold text-pink-400">{data.total_phrases}</p>
              <p className="text-xs text-patrol-muted">Abuse Phrases</p>
            </div>
            <div className="rounded-lg border border-patrol-border bg-patrol-card p-3 text-center">
              <p className="text-2xl font-bold text-purple-400">
                {Object.keys(data.models).length}
              </p>
              <p className="text-xs text-patrol-muted">ML Models</p>
            </div>
          </div>

          {/* Tabs + Search + Add */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="flex gap-2">
              {(
                [
                  ['terms', 'Terms'],
                  ['phrases', 'Phrases'],
                  ['patterns', 'Patterns'],
                  ['models', 'ML Models'],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setActiveTab(value)}
                  className={`rounded-lg border px-3 py-1.5 text-sm ${
                    activeTab === value
                      ? 'border-patrol-accent bg-patrol-accent/10 text-patrol-accent'
                      : 'border-patrol-border text-patrol-muted hover:text-patrol-text'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <input
              type="text"
              placeholder="Search dictionary…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="ml-auto rounded-lg border border-patrol-border bg-patrol-surface px-3 py-1.5 text-sm text-patrol-text placeholder:text-patrol-muted focus:border-patrol-accent focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowAddForm(!showAddForm)}
              className="rounded-lg bg-patrol-accent px-4 py-1.5 text-sm font-medium text-patrol-bg"
            >
              + Add Word
            </button>
          </div>

          {/* Add Term Form */}
          {showAddForm && (
            <div className="mb-6 rounded-xl border border-patrol-accent/30 bg-patrol-card p-5">
              <h3 className="mb-3 font-mono text-sm text-patrol-accent">Add New Abuse Term</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs text-patrol-muted">Word / Phrase</label>
                  <input
                    type="text"
                    value={newWord}
                    onChange={(e) => setNewWord(e.target.value)}
                    placeholder="e.g. kutti"
                    className="w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-sm text-patrol-text focus:border-patrol-accent focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-patrol-muted">
                    Regex Pattern (detection)
                  </label>
                  <input
                    type="text"
                    value={newRegex}
                    onChange={(e) => setNewRegex(e.target.value)}
                    placeholder={'e.g. \\b(kutti|kutiya|kuttiya)\\b'}
                    className="w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-sm font-mono text-patrol-text focus:border-patrol-accent focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-patrol-muted">
                    Category
                  </label>
                  <select
                    value={newLabel}
                    onChange={(e) => setNewLabel(e.target.value)}
                    className="w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-sm text-patrol-text focus:border-patrol-accent focus:outline-none"
                  >
                    <option value="hate_speech">Hate Speech</option>
                    <option value="sexual_harassment">Sexual Harassment</option>
                    <option value="rape_threat">Rape Threat</option>
                    <option value="threat">Threat</option>
                    <option value="stalking">Stalking</option>
                    <option value="bullying">Bullying</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-patrol-muted">
                    Confidence Score ({newScore.toFixed(2)})
                  </label>
                  <input
                    type="range"
                    min="0.5"
                    max="1.0"
                    step="0.05"
                    value={newScore}
                    onChange={(e) => setNewScore(parseFloat(e.target.value))}
                    className="w-full accent-patrol-accent"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="mb-1 block text-xs text-patrol-muted">
                    Meaning (English explanation)
                  </label>
                  <input
                    type="text"
                    value={newMeaning}
                    onChange={(e) => setNewMeaning(e.target.value)}
                    placeholder="Brief explanation of what this term means"
                    className="w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-sm text-patrol-text focus:border-patrol-accent focus:outline-none"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="mb-1 block text-xs text-patrol-muted">
                    Offender Implication (why is it harmful)
                  </label>
                  <input
                    type="text"
                    value={newImplication}
                    onChange={(e) => setNewImplication(e.target.value)}
                    placeholder="What the offender implies by using this term"
                    className="w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-sm text-patrol-text focus:border-patrol-accent focus:outline-none"
                  />
                </div>
              </div>
              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  onClick={handleAddTerm}
                  disabled={adding}
                  className="rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-patrol-bg disabled:opacity-50"
                >
                  {adding ? 'Adding…' : 'Add to Dictionary'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="rounded-lg border border-patrol-border px-4 py-2 text-sm text-patrol-muted"
                >
                  Cancel
                </button>
              </div>
              <p className="mt-3 text-xs text-patrol-muted">
                New terms take effect immediately on the next crawl. The keyword engine reloads automatically.
              </p>
            </div>
          )}

          {/* Terms Tab */}
          {activeTab === 'terms' && (
            <div className="space-y-2">
              <p className="mb-3 text-xs text-patrol-muted">
                Individual abusive terms detected by the keyword engine ({filteredTerms.length} terms)
              </p>
              {filteredTerms.map((term) => (
                <TermCard key={term.id} term={term} onRemove={handleRemoveTerm} />
              ))}
              {filteredTerms.length === 0 && (
                <p className="text-sm text-patrol-muted">No terms match your search.</p>
              )}
            </div>
          )}

          {/* Phrases Tab */}
          {activeTab === 'phrases' && (
            <div className="space-y-2">
              <p className="mb-3 text-xs text-patrol-muted">
                Compound abusive phrases ({filteredPhrases.length} phrases)
              </p>
              {filteredPhrases.map((phrase) => (
                <TermCard key={phrase.id} term={phrase} onRemove={handleRemoveTerm} />
              ))}
              {filteredPhrases.length === 0 && (
                <p className="text-sm text-patrol-muted">No phrases match your search.</p>
              )}
            </div>
          )}

          {/* Patterns Tab */}
          {activeTab === 'patterns' && (
            <div className="space-y-1">
              <p className="mb-3 text-xs text-patrol-muted">
                Raw regex patterns from abuse_lexicon.json ({filteredPatterns.length} patterns)
              </p>
              <div className="overflow-x-auto rounded-lg border border-patrol-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-patrol-border bg-patrol-surface/50 text-left text-xs text-patrol-muted">
                      <th className="px-3 py-2">Pattern (regex)</th>
                      <th className="px-3 py-2">Score</th>
                      <th className="px-3 py-2">Category</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPatterns.map((p, i) => (
                      <tr key={i} className="border-b border-patrol-border/50 hover:bg-patrol-card/50">
                        <td className="px-3 py-2 font-mono text-xs text-patrol-text">{p.regex}</td>
                        <td className="px-3 py-2">
                          <span
                            className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                              p.score >= 0.9
                                ? 'bg-red-500/20 text-red-400'
                                : p.score >= 0.75
                                  ? 'bg-orange-500/20 text-orange-400'
                                  : 'bg-amber-500/20 text-amber-400'
                            }`}
                          >
                            {p.score.toFixed(2)}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <CategoryBadge category={p.label} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Models Tab */}
          {activeTab === 'models' && (
            <div className="space-y-3">
              <p className="mb-3 text-xs text-patrol-muted">
                Hugging Face models used for toxicity classification
              </p>
              {Object.entries(data.models).map(([key, model]) => (
                <div
                  key={key}
                  className="rounded-lg border border-patrol-border bg-patrol-card p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="font-mono text-sm text-patrol-accent">{key}</h4>
                      <p className="mt-1 text-xs text-patrol-muted">{model.notes}</p>
                    </div>
                    <span className="shrink-0 rounded border border-patrol-border bg-patrol-surface px-2 py-0.5 font-mono text-xs text-patrol-text">
                      {model.task}
                    </span>
                  </div>
                  <p className="mt-2 font-mono text-xs text-purple-400">{model.id}</p>
                  {model.languages && (
                    <p className="mt-1 text-xs text-patrol-muted">
                      Languages: {model.languages.join(', ')}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </AppShell>
  )
}

function TermCard({ term, onRemove }: { term: GlossaryTerm; onRemove: (id: string) => void }) {
  return (
    <div className="rounded-lg border border-patrol-border bg-patrol-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold text-patrol-text">
              {term.display}
            </span>
            {term.categories.map((cat) => (
              <CategoryBadge key={cat} category={cat} />
            ))}
          </div>
          {term.meaning_en && (
            <p className="mt-1.5 text-xs text-patrol-muted">{term.meaning_en}</p>
          )}
          {term.offender_implication && (
            <p className="mt-1 text-xs text-pink-300/70">
              <span className="font-medium">Implication:</span> {term.offender_implication}
            </p>
          )}
          <p className="mt-1.5 font-mono text-[10px] text-patrol-muted-dim">
            Pattern: {term.detect}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onRemove(term.id)}
          className="shrink-0 rounded border border-red-500/30 px-2 py-1 text-xs text-red-400 hover:bg-red-500/10"
          title="Remove from dictionary"
        >
          Remove
        </button>
      </div>
    </div>
  )
}

function CategoryBadge({ category }: { category: string }) {
  const cls = CATEGORY_COLORS[category] || 'text-gray-400 border-gray-500/40 bg-gray-500/10'
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${cls}`}>
      {category}
    </span>
  )
}

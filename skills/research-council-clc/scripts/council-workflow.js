export const meta = {
  name: 'research-council',
  description: 'Adversarial academic review council: parallel persona reviewers, optional verification round, chair synthesis',
  whenToUse: 'Invoked by the research-council-clc skill to review a research artifact (idea, draft, proof, or repo)',
  phases: [
    { title: 'Review', detail: 'persona reviewers fan out in parallel' },
    { title: 'Verify', detail: 'adversarial refutation of CRITICAL/MAJOR findings (full tier only)' },
    { title: 'Synthesize', detail: 'chair merges all reviews into one prioritized report' },
    { title: 'Cleanup', detail: 'reclaim disk left by code execution (worktrees, venvs, clones)' },
  ],
}

// args (kept SMALL — the harness truncates large args payloads in transit, so
// prompts are TEMPLATED here rather than passed in):
//   {
//     verify:    bool,          // run the adversarial verification round
//     briefPath: string,        // abs path to the intake brief
//     agentsDir: string,        // abs path to this skill's agents/ directory
//     chairFile: string,        // persona filename for the chair, e.g. "chair.md"
//     roster: [ { key, role, file } ]   // one entry per reviewer
//   }
// key  = short id used for labels/dedup; role = human role name for the prompt;
// file = persona filename inside agentsDir.

// The harness marshals `args` to the script as a JSON *string*; a resume can
// double-encode it. Decode defensively.
let A = args
for (let i = 0; i < 2 && typeof A === 'string'; i++) {
  try { A = JSON.parse(A) } catch (e) { break }
}
if (!A || typeof A !== 'object') {
  throw new Error('research-council: could not decode args into an object (got ' + typeof A + '): ' + String(args).slice(0, 120))
}

const roster = A.roster || []
if (!roster.length) throw new Error('research-council: args.roster is empty')
if (!A.briefPath || !A.agentsDir) throw new Error('research-council: args.briefPath and args.agentsDir are required')

const join = (dir, f) => dir.replace(/\/+$/, '') + '/' + f

const reviewerPrompt = (role, file) =>
  `You are the ${role} on an adversarial academic review council (AI/ML + math). ` +
  `Read your persona instructions at ${join(A.agentsDir, file)} and follow them exactly. ` +
  `Read the intake brief at ${A.briefPath}, then read the artifact sources it lists. ` +
  `Conduct your review now. Return your review as structured output; your final message is data, not prose for a human.`

const chairPrompt = (payload) =>
  `You are the Chair / Synthesizer on an adversarial academic review council (AI/ML + math). ` +
  `Read your persona instructions at ${join(A.agentsDir, A.chairFile || 'chair.md')} and follow them exactly. ` +
  `Read the intake brief at ${A.briefPath} for context on the artifact. ` +
  `Synthesize the council output below into the final consolidated report. ` +
  `Your final message is the report markdown itself.\n\n## Council output (JSON)\n${payload}`

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['verdict', 'summary', 'findings'],
  properties: {
    verdict: { type: 'string', enum: ['accept', 'weak-accept', 'weak-reject', 'reject'] },
    summary: { type: 'string', description: 'One-paragraph overall assessment from this persona' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'title', 'body', 'fix'],
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR', 'NIT'] },
          title: { type: 'string', description: 'One-line statement of the problem' },
          body: { type: 'string', description: 'What is wrong, why it matters, concrete failure scenario' },
          evidence: { type: 'string', description: 'Citations, execution output, counterexample, or data backing the finding' },
          fix: { type: 'string', description: 'Concrete, actionable remedy' },
        },
      },
    },
    citations: { type: 'array', items: { type: 'string' }, description: 'Full references consulted (papers, URLs, repos)' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['stands', 'reasoning'],
  properties: {
    stands: { type: 'boolean', description: 'true if the finding survives refutation' },
    reasoning: { type: 'string' },
    revisedSeverity: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR', 'NIT', 'INVALID'] },
  },
}

phase('Review')
log(`Council convened: ${roster.map(r => r.key).join(', ')}`)

// Barrier justified: the verification round dedupes across ALL reviewers'
// findings, and the Chair needs every review at once.
// The Reproducibility Engineer executes code (clones repos, builds venvs), so it
// runs in a fresh, disposable git worktree — its filesystem mutations are
// contained there and swept in the Cleanup phase, never in the shared tree.
const reviews = (await parallel(roster.map(r => () => {
  const opts = { label: `review:${r.key}`, phase: 'Review', schema: REVIEW_SCHEMA }
  if (r.key === 'repro') opts.isolation = 'worktree'
  return agent(reviewerPrompt(r.role, r.file), opts)
    .then(res => (res ? { ...res, reviewer: r.key } : null))
}))).filter(Boolean)

const missing = roster.map(r => r.key).filter(k => !reviews.some(r => r.reviewer === k))
if (missing.length) log(`Reviewers failed/skipped: ${missing.join(', ')}`)
log(`${reviews.length}/${roster.length} reviews returned`)

let verified = []
if (A.verify) {
  const major = reviews.flatMap(r =>
    (r.findings || [])
      .filter(f => f.severity === 'CRITICAL' || f.severity === 'MAJOR')
      .map(f => ({ ...f, reviewer: r.reviewer }))
  )
  // Dedupe near-identical findings raised by multiple reviewers before paying
  // for verification: crude key on normalized title prefix.
  const seen = new Set()
  const unique = major.filter(f => {
    const k = f.title.toLowerCase().replace(/[^a-z0-9 ]/g, '').split(' ').slice(0, 6).join(' ')
    if (seen.has(k)) return false
    seen.add(k)
    return true
  })
  if (major.length !== unique.length) log(`Deduped ${major.length - unique.length} duplicate major findings`)

  if (unique.length) {
    phase('Verify')
    log(`Verifying ${unique.length} CRITICAL/MAJOR findings adversarially`)
    verified = (await parallel(unique.map((f, i) => () =>
      agent(
        `You are an adversarial verifier on an academic review council. Your job is to REFUTE the finding below — assume it is wrong until its evidence forces you to concede. Read the intake brief at ${A.briefPath} and the artifact sources it lists, then check the finding against the actual artifact, running searches or code as needed. If the finding misreads the artifact, cites nothing real, or the claimed failure cannot occur, it does not stand. If you write scripts to check it, keep them tiny and under the scratchpad, and delete any heavy env artifacts (venvs, clones, caches) before returning.\n\nFinding (from ${f.reviewer}):\nSeverity: ${f.severity}\nTitle: ${f.title}\nBody: ${f.body}\nEvidence: ${f.evidence || 'none given'}\nProposed fix: ${f.fix}`,
        { label: `verify:${f.reviewer}:${i}`, phase: 'Verify', schema: VERDICT_SCHEMA }
      ).then(v => (v ? { ...f, verdict: v } : null))
    ))).filter(Boolean)
    const killed = verified.filter(v => !v.verdict.stands).length
    log(`Verification: ${verified.length - killed} stand, ${killed} refuted`)
  }
}

phase('Synthesize')
const report = await agent(
  chairPrompt(JSON.stringify({ reviews, verified, reviewersFailed: missing })),
  { label: 'chair', phase: 'Synthesize', effort: 'high' }
)

// Cleanup: reclaim disk left by code execution. Only worth a janitor agent when
// something actually ran code — the repro seat, or the verification round (whose
// verifiers may write/run counterexample scripts). The repro seat's worktree is
// auto-reclaimed by the harness once emptied; the janitor prunes stale worktree
// entries and removes heavy throwaway env artifacts, while preserving the intake
// brief and the small evidence scripts the report cites.
let cleanup = null
const ranCode = roster.some(r => r.key === 'repro') || A.verify
if (ranCode) {
  phase('Cleanup')
  const briefDir = A.briefPath.replace(/\/[^/]*$/, '')
  cleanup = await agent(
    `You are the cleanup janitor for a research-council run. Reviewers may have executed code — the Reproducibility Engineer runs in a disposable git worktree and can create Python venvs, clone external repositories, and download caches; verification agents may have written small scripts under the council scratchpad directory ${briefDir}. Reclaim the heavy, throwaway disk now, carefully:\n` +
    `1. Run \`git worktree prune -v\` in the repository to drop stale worktree admin entries, then \`git worktree list\` and report any worktrees that remain (if a repro worktree lingers with leftover files, \`git worktree remove --force\` it — but never remove the main working tree or a worktree that holds the user's own uncommitted work).\n` +
    `2. Under ${briefDir}, the system temp dir, and any repro worktree, find and \`rm -rf\` throwaway environment artifacts created by this run: \`venv\`/\`.venv\`/conda env directories, pip/hf/torch caches, and cloned external repositories that are not the user's own work.\n` +
    `DO NOT delete: the intake brief, any small evidence or counterexample scripts the reviewers wrote (the report cites them by path), the report itself, or anything belonging to the user. When unsure whether something is the user's, leave it and say so explicitly.\n` +
    `Report precisely what you removed (with reclaimed sizes if easy) and what you deliberately kept. Your final message is that plain-text report.`,
    { label: 'cleanup', phase: 'Cleanup' }
  )
}

return { reviews, verified, report, cleanup }

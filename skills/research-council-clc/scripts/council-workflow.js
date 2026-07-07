export const meta = {
  name: 'research-council',
  description: 'Adversarial academic review council: parallel persona reviewers, optional verification round, chair synthesis',
  whenToUse: 'Invoked by the research-council-clc skill to review a research artifact (idea, draft, proof, or repo)',
  phases: [
    { title: 'Review', detail: 'persona reviewers fan out in parallel' },
    { title: 'Verify', detail: 'adversarial refutation of CRITICAL/MAJOR findings (full tier only)' },
    { title: 'Synthesize', detail: 'chair merges all reviews into one prioritized report' },
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
const reviews = (await parallel(roster.map(r => () =>
  agent(reviewerPrompt(r.role, r.file), { label: `review:${r.key}`, phase: 'Review', schema: REVIEW_SCHEMA })
    .then(res => (res ? { ...res, reviewer: r.key } : null))
))).filter(Boolean)

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
        `You are an adversarial verifier on an academic review council. Your job is to REFUTE the finding below — assume it is wrong until its evidence forces you to concede. Read the intake brief at ${A.briefPath} and the artifact sources it lists, then check the finding against the actual artifact, running searches or code as needed. If the finding misreads the artifact, cites nothing real, or the claimed failure cannot occur, it does not stand.\n\nFinding (from ${f.reviewer}):\nSeverity: ${f.severity}\nTitle: ${f.title}\nBody: ${f.body}\nEvidence: ${f.evidence || 'none given'}\nProposed fix: ${f.fix}`,
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

return { reviews, verified, report }

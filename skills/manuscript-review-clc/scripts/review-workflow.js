export const meta = {
  name: 'manuscript-review',
  description: 'ICLR-calibre manuscript peer review: parallel reviewer personas, optional weakness verification, area-chair meta-review',
  whenToUse: 'Invoked by the manuscript-review-clc skill to review a draft paper/manuscript',
  phases: [
    { title: 'Review', detail: 'independent reviewer personas fan out in parallel' },
    { title: 'Verify', detail: 'CRITICAL/MAJOR weaknesses checked against the manuscript (full tier only)' },
    { title: 'Meta-Review', detail: 'area chair synthesizes reviews into a meta-review and decision leaning' },
  ],
}

// args (kept SMALL — the harness truncates large args payloads in transit, so
// prompts are TEMPLATED here rather than passed in):
//   {
//     verify:    bool,          // adversarially check major weaknesses against the manuscript
//     briefPath: string,        // abs path to the intake brief
//     skillDir:  string,        // abs path to this skill's base directory (has agents/, references/)
//     roster: [ { key, role, file } ]   // one entry per reviewer persona
//   }

// The harness marshals `args` to the script as a JSON *string*; a resume can
// double-encode it. Decode defensively.
let A = args
for (let i = 0; i < 2 && typeof A === 'string'; i++) {
  try { A = JSON.parse(A) } catch (e) { break }
}
if (!A || typeof A !== 'object') {
  throw new Error('manuscript-review: could not decode args into an object (got ' + typeof A + '): ' + String(args).slice(0, 120))
}

const roster = A.roster || []
if (!roster.length) throw new Error('manuscript-review: args.roster is empty')
if (!A.briefPath || !A.skillDir) throw new Error('manuscript-review: args.briefPath and args.skillDir are required')

const base = A.skillDir.replace(/\/+$/, '')
const agentsDir = base + '/agents'
const refsDir = base + '/references'

const reviewerPrompt = (role, file) =>
  `You are ${role}, an independent reviewer for a top-tier ML venue (ICLR-style double-blind review). ` +
  `Read your persona instructions at ${agentsDir}/${file} and follow them exactly. ` +
  `Read the review-form reference at ${refsDir}/review-format.md and the calibration reference at ${refsDir}/calibration.md. ` +
  `Read the intake brief at ${A.briefPath}, then read the manuscript it points to IN FULL (for PDFs use the Read tool with the pages parameter, max 20 pages per call, iterating to the end). ` +
  `You review independently: do not assume any other reviewer exists. ` +
  `Write your review now. Return it as structured output; your final message is data, not prose for a human.`

const acPrompt = (payload) =>
  `You are the Area Chair for a top-tier ML venue (ICLR-style). ` +
  `Read your persona instructions at ${agentsDir}/area-chair.md and follow them exactly. ` +
  `Read the calibration reference at ${refsDir}/calibration.md. ` +
  `Read the intake brief at ${A.briefPath} for context on the manuscript (skim the manuscript itself as needed to arbitrate disagreements). ` +
  `Synthesize the reviews below into the final meta-review report. ` +
  `Your final message is the report markdown itself.\n\n## Reviews (JSON)\n${payload}`

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['summary', 'strengths', 'weaknesses', 'questions', 'rating', 'confidence'],
  properties: {
    summary: { type: 'string', description: 'Neutral 1-2 paragraph summary of the paper (claims + evidence), per the ICLR form' },
    soundness: { type: 'integer', minimum: 1, maximum: 4, description: 'Soundness score 1-4 (4=excellent)' },
    presentation: { type: 'integer', minimum: 1, maximum: 4, description: 'Presentation score 1-4 (4=excellent)' },
    contribution: { type: 'integer', minimum: 1, maximum: 4, description: 'Contribution score 1-4 (4=excellent)' },
    strengths: { type: 'array', items: { type: 'string' }, description: 'Specific strengths, each grounded in the manuscript' },
    weaknesses: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'title', 'body', 'evidence'],
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR'] },
          title: { type: 'string', description: 'One-line statement of the weakness' },
          body: { type: 'string', description: 'What is wrong and why it matters for the paper\'s claims' },
          evidence: { type: 'string', description: 'Where in the manuscript (section/table/figure/equation) or which citation/search result backs this' },
          fix: { type: 'string', description: 'What the authors would need to do to address it' },
        },
      },
    },
    questions: { type: 'array', items: { type: 'string' }, description: 'Questions to the authors, answerable in a rebuttal' },
    rating: { type: 'integer', minimum: 1, maximum: 10, description: 'Overall rating on the ICLR 1-10 scale' },
    confidence: { type: 'integer', minimum: 1, maximum: 5, description: 'Reviewer confidence 1-5' },
    citations: { type: 'array', items: { type: 'string' }, description: 'Prior work consulted (title + venue/URL), if any searches were run' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['stands', 'reasoning'],
  properties: {
    stands: { type: 'boolean', description: 'true if the weakness survives the check against the manuscript' },
    reasoning: { type: 'string' },
    revisedSeverity: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR', 'INVALID'] },
  },
}

phase('Review')
log(`Review panel convened: ${roster.map(r => r.key).join(', ')}`)

// Barrier justified: the verification round dedupes across ALL reviewers'
// weaknesses, and the Area Chair needs every review at once.
const reviews = (await parallel(roster.map(r => () =>
  agent(reviewerPrompt(r.role, r.file), { label: `review:${r.key}`, phase: 'Review', schema: REVIEW_SCHEMA })
    .then(res => (res ? { ...res, reviewer: r.key, role: r.role } : null))
))).filter(Boolean)

const missing = roster.map(r => r.key).filter(k => !reviews.some(r => r.reviewer === k))
if (missing.length) log(`Reviewers failed/skipped: ${missing.join(', ')}`)
log(`${reviews.length}/${roster.length} reviews returned; ratings: ${reviews.map(r => r.rating).join(', ')}`)

let verified = []
if (A.verify) {
  const major = reviews.flatMap(r =>
    (r.weaknesses || [])
      .filter(w => w.severity === 'CRITICAL' || w.severity === 'MAJOR')
      .map(w => ({ ...w, reviewer: r.reviewer }))
  )
  // Dedupe near-identical weaknesses raised by multiple reviewers before paying
  // for verification: crude key on normalized title prefix.
  const seen = new Set()
  const unique = major.filter(w => {
    const k = w.title.toLowerCase().replace(/[^a-z0-9 ]/g, '').split(' ').slice(0, 6).join(' ')
    if (seen.has(k)) return false
    seen.add(k)
    return true
  })
  if (major.length !== unique.length) log(`Deduped ${major.length - unique.length} duplicate major weaknesses`)

  if (unique.length) {
    phase('Verify')
    log(`Checking ${unique.length} CRITICAL/MAJOR weaknesses against the manuscript`)
    verified = (await parallel(unique.map((w, i) => () =>
      agent(
        `You are an adversarial checker on a peer-review panel. A reviewer raised the weakness below against a manuscript. Your job is to REFUTE it — assume the reviewer misread the paper until the manuscript itself forces you to concede. Read the intake brief at ${A.briefPath}, then read the relevant parts of the manuscript it points to (for PDFs use the Read tool with the pages parameter). A weakness does not stand if the paper already addresses it, if it misquotes the paper, or if the claimed problem cannot affect the paper's conclusions. Reviewer hallucinations (criticizing content that is not in the paper, or missing content that is) must be killed.\n\nWeakness (from ${w.reviewer}):\nSeverity: ${w.severity}\nTitle: ${w.title}\nBody: ${w.body}\nEvidence: ${w.evidence || 'none given'}\nProposed fix: ${w.fix || 'none given'}`,
        { label: `verify:${w.reviewer}:${i}`, phase: 'Verify', schema: VERDICT_SCHEMA }
      ).then(v => (v ? { ...w, verdict: v } : null))
    ))).filter(Boolean)
    const killed = verified.filter(v => !v.verdict.stands).length
    log(`Verification: ${verified.length - killed} stand, ${killed} refuted`)
  }
}

phase('Meta-Review')
const report = await agent(
  acPrompt(JSON.stringify({ reviews, verified, reviewersFailed: missing })),
  { label: 'area-chair', phase: 'Meta-Review', effort: 'high' }
)

return { reviews, verified, report }

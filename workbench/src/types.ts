export type PreviewPart = { name: string; file: string; color: string }

export type ReviewAnnotation = {
  id: string
  label: string
  position_mm: [number, number, number]
  part?: string | null
  description?: string
  color?: string
}

export type DesignDelta = {
  annotation_id: string
  parameter: string
  before: number
  after: number
  delta: number
  unit: string
  direction: string
  reason: string
  review_status: string
}

export type PreviewManifest = {
  title: string
  parts: PreviewPart[]
  annotations?: ReviewAnnotation[]
  deltas?: DesignDelta[]
  progress_url?: string
}

export type ProgressAnswer = {
  id: string
  question: string
  answer: string
  source: string
  status: "confirmed" | "assumed" | "needs-confirmation"
  recorded_at: string
}

export type ProgressStep = {
  id: string
  title: string
  status: "pending" | "in-progress" | "blocked" | "complete"
  summary: string
  evidence: string[]
  updated_at: string
}

export type ProgressLearning = {
  id: string
  statement: string
  evidence: string
  status: "candidate" | "validated" | "promoted"
  applies_to: string
  recorded_at: string
}

export type ReviewReply = {
  id: string
  author: "user" | "agent"
  message: string
  created_at: string
}

export type ReviewComment = {
  id: string
  part: string
  position_mm: [number, number, number]
  message: string
  author: "user" | "agent"
  status: "open" | "acknowledged" | "resolved"
  created_at: string
  updated_at: string
  replies: ReviewReply[]
}

export type DesignProgress = {
  schema_version: 1
  design_id: string
  title: string
  status: "active" | "blocked" | "ready-for-review" | "complete"
  phase: string
  summary: string
  updated_at: string
  answers: ProgressAnswer[]
  steps: ProgressStep[]
  learnings: ProgressLearning[]
  review_comments: ReviewComment[]
}

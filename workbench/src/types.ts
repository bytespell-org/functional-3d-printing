export type PreviewPart = { name: string; file: string; color: string }

export type ReviewAnnotation = {
  id: string
  label: string
  position_mm: [number, number, number]
  part?: string | null
  description?: string
  color?: string
}

export type PreviewManifest = {
  title: string
  parts: PreviewPart[]
  annotations?: ReviewAnnotation[]
  progress_url?: string
}

export type ProgressItem = {
  id: string
  title: string
  summary: string
  updated_at: string
}

export type ReviewComment = {
  id: string
  part: string
  position_mm: [number, number, number]
  message: string
  author: "user" | "agent"
  created_at: string
  updated_at: string
}

export type DesignProgress = {
  schema_version: 2
  design_id: string
  title: string
  summary: string
  updated_at: string
  progress: ProgressItem[]
  comments: ReviewComment[]
}

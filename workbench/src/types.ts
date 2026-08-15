export type PreviewPart = {
  name: string
  file: string
  color: string
  role?: "printable"
}

export type PreviewReference = {
  name: string
  file: string
  color: string
  role: "reference"
  opacity?: number
  position_mm?: [number, number, number]
  rotation_deg?: [number, number, number]
  nominal_size_mm?: [number, number, number] | null
  notes?: string[]
  source_id?: string | null
}

export type ReviewAnnotation = {
  id: string
  label: string
  position_mm: [number, number, number]
  part?: string | null
  description?: string
  color?: string
}

export type PreviewManifest = {
  revision?: string
  title: string
  parts: PreviewPart[]
  references?: PreviewReference[]
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
  created_at: string
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

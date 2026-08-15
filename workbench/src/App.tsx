import { useCallback, useEffect, useState } from "react"
import { CommentAdd01Icon, Delete02Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ThreeViewer } from "@/components/three-viewer"
import type { DesignProgress, PreviewManifest, ReviewComment } from "@/types"

type CommentAnchor = {
  part: string
  position_mm: [number, number, number]
  screen_position_px: [number, number]
  viewport_size_px: [number, number]
}

type SelectedComment = ReviewComment & {
  screen_position_px: [number, number]
  viewport_size_px: [number, number]
}

export function App() {
  const [manifest, setManifest] = useState<PreviewManifest | null>(null)
  const [progress, setProgress] = useState<DesignProgress | null>(null)
  const [error, setError] = useState("")
  const [panelOpen, setPanelOpen] = useState(false)
  const [commentMode, setCommentMode] = useState(false)
  const [measureMode, setMeasureMode] = useState(false)
  const [commentAnchor, setCommentAnchor] = useState<CommentAnchor | null>(null)
  const [commentText, setCommentText] = useState("")
  const [selectedComment, setSelectedComment] =
    useState<SelectedComment | null>(null)
  const [postingComment, setPostingComment] = useState(false)
  const [removingComment, setRemovingComment] = useState("")

  useEffect(() => {
    let stopped = false
    let hasManifest = false
    let timer = 0
    const refresh = () => {
      void fetch("manifest.json", { cache: "no-store" })
        .then((response) => {
          if (!response.ok) throw new Error(`manifest ${response.status}`)
          return response.json()
        })
        .then((value: PreviewManifest) => {
          if (stopped) return
          const firstManifest = !hasManifest
          hasManifest = true
          setManifest((current) => {
            const currentRevision = current?.revision || JSON.stringify(current)
            const nextRevision = value.revision || JSON.stringify(value)
            return currentRevision === nextRevision ? current : value
          })
          if (firstManifest) setError("")
        })
        .catch((reason: unknown) => {
          if (!stopped && !hasManifest)
            setError(reason instanceof Error ? reason.message : String(reason))
        })
        .finally(() => {
          if (!stopped) timer = window.setTimeout(refresh, 750)
        })
    }
    refresh()
    return () => {
      stopped = true
      window.clearTimeout(timer)
    }
  }, [])

  useEffect(() => {
    if (!manifest) return
    const progressUrl = manifest.progress_url || "../progress.json"
    let stopped = false
    let timer = 0
    const refresh = () => {
      void fetch(progressUrl, { cache: "no-store" })
        .then((response) => {
          if (!response.ok) throw new Error(`progress ${response.status}`)
          return response.json()
        })
        .then((value: DesignProgress) => {
          if (!stopped) {
            setProgress(value)
            setError("")
          }
        })
        .catch((reason: unknown) => {
          if (!stopped)
            setError(reason instanceof Error ? reason.message : String(reason))
        })
        .finally(() => {
          if (!stopped) timer = window.setTimeout(refresh, 750)
        })
    }
    refresh()
    return () => {
      stopped = true
      window.clearTimeout(timer)
    }
  }, [manifest])

  const pickCommentAnchor = useCallback((anchor: CommentAnchor) => {
    setCommentAnchor(anchor)
    setCommentText("")
    setCommentMode(false)
    setSelectedComment(null)
    setPanelOpen(false)
  }, [])

  const toggleCommentMode = () => {
    const next = !commentMode
    setCommentMode(next)
    if (next) setMeasureMode(false)
    setCommentAnchor(null)
    setSelectedComment(null)
    if (next) setPanelOpen(false)
  }

  const postComment = async () => {
    if (!commentAnchor || !commentText.trim()) return
    setPostingComment(true)
    try {
      const response = await fetch("/api/review-comments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          part: commentAnchor.part,
          position_mm: commentAnchor.position_mm,
          message: commentText.trim(),
        }),
      })
      const value = (await response.json()) as { ok: boolean; error?: string }
      if (!response.ok || !value.ok)
        throw new Error(value.error || `comment ${response.status}`)
      setCommentAnchor(null)
      setCommentText("")
      setError("")
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setPostingComment(false)
    }
  }

  const removeComment = async (id: string) => {
    setRemovingComment(id)
    try {
      const response = await fetch(
        `/api/review-comments/${encodeURIComponent(id)}`,
        { method: "DELETE" }
      )
      const value = (await response.json()) as { ok: boolean; error?: string }
      if (!response.ok || !value.ok)
        throw new Error(value.error || `comment ${response.status}`)
      setProgress((current) =>
        current
          ? {
              ...current,
              comments: current.comments.filter((comment) => comment.id !== id),
            }
          : current
      )
      setSelectedComment((current) => (current?.id === id ? null : current))
      setError("")
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setRemovingComment("")
    }
  }

  if (!manifest)
    return (
      <div className="grid min-h-svh place-items-center bg-background text-sm text-muted-foreground">
        {error || "Loading…"}
      </div>
    )

  const comments = progress?.comments || []
  const composerWidth = commentAnchor
    ? Math.min(320, commentAnchor.viewport_size_px[0] - 16)
    : 320
  const composerLeft = commentAnchor
    ? Math.max(
        8,
        Math.min(
          commentAnchor.screen_position_px[0] - composerWidth / 2,
          commentAnchor.viewport_size_px[0] - composerWidth - 8
        )
      )
    : 8
  const composerTop = commentAnchor
    ? commentAnchor.screen_position_px[1] <
      commentAnchor.viewport_size_px[1] / 2
      ? commentAnchor.screen_position_px[1] + 16
      : Math.max(8, commentAnchor.screen_position_px[1] - 212)
    : 8
  const selectedWidth = selectedComment
    ? Math.min(280, selectedComment.viewport_size_px[0] - 16)
    : 280
  const selectedLeft = selectedComment
    ? Math.max(
        8,
        Math.min(
          selectedComment.screen_position_px[0] - selectedWidth / 2,
          selectedComment.viewport_size_px[0] - selectedWidth - 8
        )
      )
    : 8
  const selectedTop = selectedComment
    ? selectedComment.screen_position_px[1] <
      selectedComment.viewport_size_px[1] / 2
      ? selectedComment.screen_position_px[1] + 14
      : Math.max(8, selectedComment.screen_position_px[1] - 132)
    : 8

  return (
    <TooltipProvider>
      <div className="dark flex h-dvh min-h-0 flex-col overflow-hidden bg-background text-foreground lg:min-h-[34rem]">
        <main className="min-h-0 flex-1 p-2">
          <section className="relative h-full min-h-0 overflow-hidden lg:min-h-[28rem]">
            <ThreeViewer
              manifest={manifest}
              reviewComments={comments}
              commentMode={commentMode}
              onCommentModeChange={setCommentMode}
              measureMode={measureMode}
              onMeasureModeChange={setMeasureMode}
              onPickComment={pickCommentAnchor}
              onSelectComment={setSelectedComment}
            />

            <div className="absolute top-2 right-2 z-30 flex gap-1 lg:right-[21rem]">
              <Button
                size="sm"
                className="size-9 border border-sky-300/50 bg-sky-500 p-0 text-sky-950 shadow-lg hover:bg-sky-400"
                aria-label={
                  commentMode ? "Cancel adding comment" : "Add comment"
                }
                title={commentMode ? "Cancel adding comment" : "Add comment"}
                aria-pressed={commentMode}
                onClick={toggleCommentMode}
              >
                <HugeiconsIcon
                  icon={CommentAdd01Icon}
                  size={18}
                  strokeWidth={1.9}
                />
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="h-9 shadow-lg lg:hidden"
                onClick={() => setPanelOpen(true)}
              >
                Progress
              </Button>
            </div>

            {commentMode && (
              <div className="pointer-events-none absolute top-13 left-2 z-30 rounded-md bg-primary px-2.5 py-1.5 text-xs font-medium text-primary-foreground shadow-lg lg:top-12">
                Tap the model to place your comment
              </div>
            )}

            {commentAnchor && (
              <>
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute z-40 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-amber-400 shadow"
                  style={{
                    left: commentAnchor.screen_position_px[0],
                    top: commentAnchor.screen_position_px[1],
                  }}
                />
                <div
                  className="absolute z-50 space-y-2 rounded-xl border bg-card/98 p-3 shadow-2xl backdrop-blur-xl"
                  style={{
                    width: composerWidth,
                    left: composerLeft,
                    top: composerTop,
                  }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-xs font-medium">
                      {commentAnchor.part}
                    </p>
                    <span className="text-[10px] text-muted-foreground tabular-nums">
                      {commentAnchor.position_mm
                        .map((value) => value.toFixed(1))
                        .join(", ")}
                    </span>
                  </div>
                  <textarea
                    autoFocus
                    aria-label="Model comment"
                    value={commentText}
                    onChange={(event) => setCommentText(event.target.value)}
                    onKeyDown={(event) => {
                      if (
                        (event.metaKey || event.ctrlKey) &&
                        event.key === "Enter"
                      )
                        void postComment()
                    }}
                    placeholder="What should change here?"
                    className="min-h-24 w-full resize-y rounded-md border bg-background px-3 py-2 text-base leading-6 outline-none focus-visible:ring-2 focus-visible:ring-ring lg:min-h-20 lg:px-2 lg:py-1.5 lg:text-xs lg:leading-5"
                  />
                  <div className="flex justify-end gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setCommentAnchor(null)}
                    >
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      disabled={!commentText.trim() || postingComment}
                      onClick={() => void postComment()}
                    >
                      {postingComment ? "Posting…" : "Post"}
                    </Button>
                  </div>
                </div>
              </>
            )}

            {selectedComment && !commentAnchor && (
              <div
                className="absolute z-50 rounded-xl border border-sky-300/30 bg-card/96 p-3 shadow-2xl backdrop-blur-xl"
                style={{
                  width: selectedWidth,
                  left: selectedLeft,
                  top: selectedTop,
                }}
              >
                <div className="flex items-start gap-2">
                  <p className="min-w-0 flex-1 text-xs leading-5">
                    {selectedComment.message}
                  </p>
                  <Button
                    size="icon-xs"
                    variant="ghost"
                    aria-label={`Delete comment on ${selectedComment.part}`}
                    disabled={removingComment === selectedComment.id}
                    onClick={() => void removeComment(selectedComment.id)}
                  >
                    <HugeiconsIcon
                      icon={Delete02Icon}
                      size={15}
                      strokeWidth={1.8}
                    />
                  </Button>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="mt-1 h-7 px-2 text-[11px]"
                  onClick={() => setSelectedComment(null)}
                >
                  Close
                </Button>
              </div>
            )}

            {panelOpen && (
              <button
                aria-label="Close progress"
                className="absolute inset-0 z-30 bg-black/45 lg:hidden"
                onClick={() => setPanelOpen(false)}
              />
            )}

            <aside
              aria-label="Progress"
              className={`${
                panelOpen ? "flex" : "hidden"
              } absolute inset-x-2 bottom-2 z-40 max-h-[72dvh] min-h-72 flex-col overflow-hidden rounded-xl border bg-card/96 shadow-2xl backdrop-blur-xl lg:top-2 lg:right-2 lg:bottom-auto lg:left-auto lg:flex lg:h-[min(32rem,calc(100%-1rem))] lg:min-h-0 lg:w-80 lg:rounded-lg`}
            >
              <div className="flex shrink-0 items-center justify-between gap-2 border-b px-3 py-2">
                <p className="text-xs font-medium">Progress</p>
                <Button
                  size="sm"
                  variant="ghost"
                  className="lg:hidden"
                  onClick={() => setPanelOpen(false)}
                >
                  Close
                </Button>
              </div>

              <ScrollArea className="min-h-0 flex-1">
                <div className="divide-y">
                  {progress?.summary && (
                    <p className="p-3 text-xs leading-5">{progress.summary}</p>
                  )}
                  {progress?.progress.map((item) => (
                    <div key={item.id} className="p-3">
                      <p className="truncate text-xs font-medium">
                        {item.title}
                      </p>
                      {item.summary && (
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">
                          {item.summary}
                        </p>
                      )}
                    </div>
                  ))}
                  {!progress?.summary && !progress?.progress.length && (
                    <p className="p-4 text-center text-xs text-muted-foreground">
                      No progress updates yet.
                    </p>
                  )}
                </div>
              </ScrollArea>

              {error && (
                <div className="shrink-0 border-t bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  {error}
                </div>
              )}
            </aside>
          </section>
        </main>
      </div>
    </TooltipProvider>
  )
}

export default App

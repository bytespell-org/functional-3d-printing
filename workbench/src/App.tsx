import { useCallback, useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ThreeViewer } from "@/components/three-viewer"
import type {
  DesignProgress,
  PreviewManifest,
  ReviewComment,
} from "@/types"

type CommentAnchor = {
  part: string
  position_mm: [number, number, number]
}

export function App() {
  const [manifest, setManifest] = useState<PreviewManifest | null>(null)
  const [progress, setProgress] = useState<DesignProgress | null>(null)
  const [error, setError] = useState("")
  const [tab, setTab] = useState("comments")
  const [commentAnchor, setCommentAnchor] = useState<CommentAnchor | null>(null)
  const [commentText, setCommentText] = useState("")
  const [postingComment, setPostingComment] = useState(false)
  const [removingComment, setRemovingComment] = useState("")
  const [mobilePanelOpen, setMobilePanelOpen] = useState(false)

  useEffect(() => {
    fetch("manifest.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`manifest ${response.status}`)
        return response.json()
      })
      .then((value: PreviewManifest) => setManifest(value))
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : String(reason))
      )
  }, [])

  useEffect(() => {
    if (!manifest) return
    const progressUrl = manifest.progress_url || "../progress.json"
    let stopped = false
    const refresh = () =>
      fetch(progressUrl, { cache: "no-store" })
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
    void refresh()
    const timer = window.setInterval(refresh, 2000)
    return () => {
      stopped = true
      window.clearInterval(timer)
    }
  }, [manifest])

  const pickCommentAnchor = useCallback((anchor: CommentAnchor) => {
    setCommentAnchor(anchor)
    setCommentText("")
    setTab("comments")
  }, [])

  const postComment = async () => {
    if (!commentAnchor || !commentText.trim()) return
    setPostingComment(true)
    try {
      const response = await fetch("/api/review-comments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...commentAnchor,
          message: commentText.trim(),
        }),
      })
      const value = (await response.json()) as {
        ok: boolean
        error?: string
      }
      if (!response.ok || !value.ok)
        throw new Error(value.error || `comment ${response.status}`)
      setCommentAnchor(null)
      setCommentText("")
      setTab("comments")
      setMobilePanelOpen(true)
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
      const response = await fetch(`/api/review-comments/${encodeURIComponent(id)}`, {
        method: "DELETE",
      })
      const value = (await response.json()) as { ok: boolean; error?: string }
      if (!response.ok || !value.ok)
        throw new Error(value.error || `comment ${response.status}`)
      setProgress((current) =>
        current
          ? { ...current, comments: current.comments.filter((comment) => comment.id !== id) }
          : current
      )
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

  return (
    <TooltipProvider>
      <div className="dark flex h-dvh min-h-0 flex-col overflow-hidden bg-background text-foreground lg:min-h-[34rem]">
        <header className="flex h-11 shrink-0 items-center gap-2 border-b bg-card px-3 lg:h-12 lg:gap-3">
          <h1 className="min-w-0 flex-1 truncate font-heading text-base font-semibold tracking-tight">
            {progress?.title || manifest.title}
          </h1>
          {!!progress?.comments?.length && (
            <span className="text-xs text-muted-foreground sm:hidden">
              {progress.comments.length} comment{progress.comments.length === 1 ? "" : "s"}
            </span>
          )}
        </header>

        <main className="relative grid min-h-0 flex-1 gap-2 p-2 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <section className="min-h-0 overflow-hidden lg:min-h-[28rem]">
            <ThreeViewer
              manifest={manifest}
              reviewComments={progress?.comments || []}
              onPickComment={pickCommentAnchor}
              onOpenReview={() => {
                setTab("comments")
                setMobilePanelOpen(true)
              }}
            />
          </section>

          {mobilePanelOpen && (
            <button
              aria-label="Close review panel"
              className="fixed inset-0 z-30 bg-black/60 lg:hidden"
              onClick={() => setMobilePanelOpen(false)}
            />
          )}

          <aside
            className={`${
              mobilePanelOpen ? "fixed" : "hidden"
            } inset-x-2 top-13 bottom-2 z-40 min-h-0 overflow-hidden rounded-lg border bg-card shadow-2xl lg:static lg:block lg:rounded-none lg:shadow-none`}
          >
            <Tabs
              value={tab}
              onValueChange={setTab}
              className="flex h-full flex-col"
            >
              <div className="flex h-11 shrink-0 items-center justify-between border-b px-3 lg:hidden">
                <p className="text-sm font-semibold">Review</p>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setMobilePanelOpen(false)}
                >
                  Close
                </Button>
              </div>
              <TabsList className="grid h-10 w-full shrink-0 grid-cols-2 rounded-none border-b bg-transparent p-1 lg:h-9">
                <TabsTrigger value="comments">Comments</TabsTrigger>
                <TabsTrigger value="progress">Progress</TabsTrigger>
              </TabsList>

              <ScrollArea className="min-h-0 flex-1">
                <TabsContent value="comments" className="m-0 divide-y">
                  {commentAnchor && (
                    <div className="hidden space-y-2 p-3 lg:block">
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
                        className="min-h-20 w-full resize-y rounded-md border bg-background px-2 py-1.5 text-xs leading-5 outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
                  )}
                  {(progress?.comments || []).map(
                    (comment: ReviewComment, index) => (
                      <div key={comment.id} className="p-3">
                        <div className="flex items-start gap-2">
                          <span className="grid size-5 shrink-0 place-items-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                            {index + 1}
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <p className="truncate text-xs font-medium">
                                {comment.part}
                              </p>
                              <Button
                                size="sm"
                                variant="ghost"
                                aria-label={`Delete comment on ${comment.part}`}
                                disabled={removingComment === comment.id}
                                onClick={() => void removeComment(comment.id)}
                              >
                                {removingComment === comment.id ? "Deleting…" : "Delete"}
                              </Button>
                            </div>
                            <p className="mt-1 text-xs leading-5">
                              {comment.message}
                            </p>
                          </div>
                        </div>
                      </div>
                    )
                  )}
                  {!commentAnchor && !progress?.comments?.length && (
                    <p className="p-3 text-xs leading-5 text-muted-foreground">
                      Choose Comment, then click the model.
                    </p>
                  )}
                </TabsContent>

                <TabsContent value="progress" className="m-0 divide-y">
                  {progress?.summary && (
                    <p className="p-3 text-xs leading-5">{progress.summary}</p>
                  )}
                  {progress?.progress.map((item) => (
                    <div key={item.id} className="p-3">
                      <p className="truncate text-xs font-medium">{item.title}</p>
                      {item.summary && (
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">
                          {item.summary}
                        </p>
                      )}
                    </div>
                  ))}
                </TabsContent>
              </ScrollArea>
            </Tabs>
            {error && (
              <div className="border-t bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {error}
              </div>
            )}
          </aside>
        </main>

        {commentAnchor && (
          <div className="fixed inset-x-2 bottom-[max(0.5rem,env(safe-area-inset-bottom))] z-50 rounded-xl border bg-card p-3 shadow-2xl lg:hidden">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="truncate text-sm font-medium">
                Comment on {commentAnchor.part}
              </p>
              <button
                className="text-xs text-muted-foreground"
                onClick={() => setCommentAnchor(null)}
              >
                Cancel
              </button>
            </div>
            <textarea
              autoFocus
              aria-label="Model comment"
              value={commentText}
              onChange={(event) => setCommentText(event.target.value)}
              placeholder="What should change here?"
              className="min-h-24 w-full resize-none rounded-lg border bg-background px-3 py-2 text-base leading-6 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <Button
              className="mt-2 w-full"
              disabled={!commentText.trim() || postingComment}
              onClick={() => void postComment()}
            >
              {postingComment ? "Posting…" : "Post comment"}
            </Button>
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}

export default App

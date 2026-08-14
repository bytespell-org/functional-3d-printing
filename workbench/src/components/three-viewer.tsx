import { useEffect, useRef, useState } from "react"
import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js"

import { Button } from "@/components/ui/button"
import type { PreviewManifest, ReviewComment } from "@/types"

type Projection = "ortho" | "perspective"
type RenderMode = "solid" | "xray"

type ViewerApi = {
  fit: () => void
  setGrid: (visible: boolean) => void
  setLabels: (visible: boolean) => void
  setCommentMode: (enabled: boolean) => void
  setMeasure: (enabled: boolean) => void
  setPartVisible: (name: string, visible: boolean) => void
  setProjection: (projection: Projection) => void
  setRenderMode: (mode: RenderMode) => void
  setReviewComments: (comments: ReviewComment[]) => void
}

function makeLabelSprite(
  text: string,
  color: string,
  height: number,
  variant: "annotation" | "comment" = "annotation"
) {
  const fontSize = 40
  const lineHeight = 48
  const paddingX = 22
  const paddingY = 12
  const maximumTextWidth = variant === "comment" ? 600 : 460
  const canvas = document.createElement("canvas")
  const context = canvas.getContext("2d")
  if (!context) throw new Error("Canvas labels are unavailable")
  context.font = `600 ${fontSize}px Inter, system-ui, sans-serif`
  const words = text.trim().split(/\s+/)
  const lines: string[] = []
  let currentLine = ""
  for (const word of words) {
    const candidate = currentLine ? `${currentLine} ${word}` : word
    if (
      currentLine &&
      context.measureText(candidate).width > maximumTextWidth
    ) {
      lines.push(currentLine)
      currentLine = word
    } else {
      currentLine = candidate
    }
  }
  if (currentLine) lines.push(currentLine)
  if (!lines.length) lines.push(text)
  const textWidth = Math.max(
    ...lines.map((line) => context.measureText(line).width)
  )
  const width = Math.ceil(textWidth + paddingX * 2)
  const canvasHeight = lineHeight * lines.length + paddingY * 2
  canvas.width = width
  canvas.height = canvasHeight
  context.font = `600 ${fontSize}px Inter, system-ui, sans-serif`
  context.fillStyle =
    variant === "comment"
      ? "rgba(56, 189, 248, 0.76)"
      : "rgba(23, 21, 26, 0.78)"
  context.strokeStyle =
    variant === "comment" ? "rgba(186, 230, 253, 0.88)" : color
  context.lineWidth = variant === "comment" ? 2 : 3
  context.beginPath()
  context.roundRect(
    1.5,
    1.5,
    width - 3,
    canvasHeight - 3,
    variant === "comment" ? 10 : 16
  )
  context.fill()
  context.stroke()
  context.fillStyle = variant === "comment" ? "#082f49" : "rgba(250,250,250,0.94)"
  context.textAlign = "center"
  context.textBaseline = "middle"
  lines.forEach((line, index) => {
    context.fillText(
      line,
      width / 2,
      paddingY + lineHeight * (index + 0.5) + 1
    )
  })

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.minFilter = THREE.LinearFilter
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  })
  const sprite = new THREE.Sprite(material)
  const worldHeight = height * lines.length
  sprite.scale.set(worldHeight * (width / canvasHeight), worldHeight, 1)
  sprite.renderOrder = 1000
  return sprite
}

export function ThreeViewer({
  manifest,
  reviewComments,
  commentMode,
  onCommentModeChange,
  measureMode,
  onMeasureModeChange,
  onPickComment,
}: {
  manifest: PreviewManifest
  reviewComments: ReviewComment[]
  commentMode: boolean
  onCommentModeChange: (enabled: boolean) => void
  measureMode: boolean
  onMeasureModeChange: (enabled: boolean) => void
  onPickComment: (anchor: {
    part: string
    position_mm: [number, number, number]
    screen_position_px: [number, number]
    viewport_size_px: [number, number]
  }) => void
}) {
  const hostRef = useRef<HTMLDivElement>(null)
  const apiRef = useRef<ViewerApi | null>(null)
  const commentsRef = useRef(reviewComments)
  const visibilityRef = useRef(
    new Map(manifest.parts.map((part) => [part.name, true]))
  )
  const [grid, setGrid] = useState(true)
  const [labels, setLabels] = useState(true)
  const [renderMode, setRenderMode] = useState<RenderMode>("solid")
  const [message, setMessage] = useState("Loading…")
  const [partVisibility, setPartVisibility] = useState<Record<string, boolean>>(
    () => Object.fromEntries(manifest.parts.map((part) => [part.name, true]))
  )

  useEffect(() => {
    commentsRef.current = reviewComments
    apiRef.current?.setReviewComments(reviewComments)
  }, [reviewComments])

  useEffect(() => {
    apiRef.current?.setCommentMode(commentMode)
  }, [commentMode])

  useEffect(() => {
    apiRef.current?.setMeasure(measureMode)
  }, [measureMode])

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    host.replaceChildren()

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    renderer.setClearColor(0x17151a)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    host.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const root = new THREE.Group()
    scene.add(root)
    scene.add(new THREE.HemisphereLight(0xffffff, 0x332b39, 2.4))
    const key = new THREE.DirectionalLight(0xfff7e8, 2.2)
    key.position.set(4, -6, 8)
    scene.add(key)

    const cameras = {
      perspective: new THREE.PerspectiveCamera(42, 1, 0.01, 100000),
      ortho: new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 100000),
    }
    Object.values(cameras).forEach((item) => item.up.set(0, 0, 1))
    let camera: THREE.Camera = cameras.ortho
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.rotateSpeed = 0.7
    controls.zoomSpeed = 0.9
    controls.panSpeed = 0.8
    controls.screenSpacePanning = true
    controls.minPolarAngle = 0.02
    controls.maxPolarAngle = Math.PI - 0.02
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE
    controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY
    controls.mouseButtons.RIGHT = THREE.MOUSE.PAN
    controls.touches.ONE = THREE.TOUCH.ROTATE
    controls.touches.TWO = THREE.TOUCH.DOLLY_PAN
    controls.cursorStyle = "grab"

    const gridHelper = new THREE.GridHelper(200, 40, 0x7c6579, 0x342d37)
    gridHelper.rotation.x = Math.PI / 2
    scene.add(gridHelper)

    const meshes: THREE.Mesh[] = []
    const meshByName = new Map<string, THREE.Mesh>()
    const annotationGroups: THREE.Group[] = []
    let reviewGroups: THREE.Group[] = []
    const bounds = new THREE.Box3()
    let measureMode = false
    let commentMode = false
    let labelsVisible = true
    let initialView: {
      center: THREE.Vector3
      position: THREE.Vector3
      orthoSize: number
    } | null = null
    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    let measurePoints: THREE.Vector3[] = []
    let measureLine: THREE.Line | null = null
    let markers: THREE.Mesh[] = []

    const disposeObject = (object: THREE.Object3D) => {
      object.traverse((child) => {
        if (child instanceof THREE.Mesh || child instanceof THREE.Line) {
          child.geometry.dispose()
          const materials = Array.isArray(child.material)
            ? child.material
            : [child.material]
          materials.forEach((material) => material.dispose())
        }
        if (child instanceof THREE.Sprite) {
          child.material.map?.dispose()
          child.material.dispose()
        }
      })
    }

    const drawReviewComments = (comments: ReviewComment[]) => {
      reviewGroups.forEach((group) => {
        group.removeFromParent()
        disposeObject(group)
      })
      reviewGroups = []
      comments.forEach((item, index) => {
        const owner = meshByName.get(item.part)
        if (!owner) return
        const point = new THREE.Vector3(...item.position_mm)
        const sphere = owner.geometry.boundingSphere
        const radius = Math.max(sphere?.radius || 20, 1)
        const offset = point.clone().sub(sphere?.center || new THREE.Vector3())
        if (offset.lengthSq() < 0.0001) offset.set(0, 0, 1)
        const radial = offset
          .clone()
          .normalize()
          .multiplyScalar(Math.max(radius * 0.46, 9))
        const tangent = new THREE.Vector3(-offset.y, offset.x, 0)
        if (tangent.lengthSq() < 0.0001) tangent.set(1, 0, 0)
        const fan =
          (index - (comments.length - 1) / 2) * Math.max(radius * 0.28, 5)
        offset.copy(radial.add(tangent.normalize().multiplyScalar(fan)))
        const color = "#38bdf8"
        const group = new THREE.Group()
        group.position.copy(point)
        group.visible = labelsVisible
        const leader = new THREE.Mesh(
          new THREE.CylinderGeometry(
            Math.max(radius * 0.004, 0.1),
            Math.max(radius * 0.004, 0.1),
            offset.length(),
            8
          ),
          new THREE.MeshBasicMaterial({
            color,
            depthTest: false,
            depthWrite: false,
          })
        )
        leader.renderOrder = 999
        leader.position.copy(offset).multiplyScalar(0.5)
        leader.quaternion.setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          offset.clone().normalize()
        )
        const dot = new THREE.Mesh(
          new THREE.SphereGeometry(Math.max(radius * 0.015, 0.2), 12, 8),
          new THREE.MeshBasicMaterial({
            color,
            depthTest: false,
            depthWrite: false,
          })
        )
        dot.renderOrder = 999
        const label = makeLabelSprite(
          item.message,
          color,
          Math.max(radius * 0.067, 2.5),
          "comment"
        )
        label.position.copy(offset)
        group.add(leader, dot, label)
        owner.add(group)
        reviewGroups.push(group)
      })
    }

    const updateOrtho = () => {
      const aspect = Math.max(
        host.clientWidth / Math.max(host.clientHeight, 1),
        0.1
      )
      const size =
        (initialView?.orthoSize || 100) / Math.min(Math.max(aspect, 0.1), 1)
      Object.assign(cameras.ortho, {
        left: -size * aspect,
        right: size * aspect,
        top: size,
        bottom: -size,
      })
      cameras.ortho.updateProjectionMatrix()
    }
    const resize = () => {
      const width = host.clientWidth
      const height = host.clientHeight
      // Keep the canvas's CSS box matched to the viewer host. With
      // updateStyle=false, high-DPI drawing-buffer pixels become layout pixels
      // in browsers that do not supply an external canvas size rule, leaving
      // the correctly fitted model clipped in one corner of an oversized canvas.
      renderer.setSize(width, height)
      cameras.perspective.aspect = width / Math.max(height, 1)
      cameras.perspective.updateProjectionMatrix()
      updateOrtho()
    }
    const fit = () => {
      bounds.makeEmpty()
      meshes.forEach((mesh) => bounds.expandByObject(mesh))
      if (bounds.isEmpty()) return
      const sphere = bounds.getBoundingSphere(new THREE.Sphere())
      const center = sphere.center
      const radius = Math.max(sphere.radius, 1)
      const position = center
        .clone()
        .add(
          new THREE.Vector3(1.3, -1.6, 1.1)
            .normalize()
            .multiplyScalar(radius * 3.2)
        )
      Object.values(cameras).forEach((item) => {
        item.position.copy(position)
        item.up.set(0, 0, 1)
        item.lookAt(center)
      })
      controls.target.copy(center)
      cameras.perspective.near = Math.max(radius / 1000, 0.01)
      cameras.perspective.far = radius * 100
      cameras.perspective.updateProjectionMatrix()
      initialView = {
        center: center.clone(),
        position: position.clone(),
        orthoSize: radius * 1.25,
      }
      updateOrtho()
      controls.update()
    }
    const clearMeasure = () => {
      measurePoints = []
      markers.forEach((marker) => scene.remove(marker))
      markers = []
      if (measureLine) scene.remove(measureLine)
      measureLine = null
    }
    const addMeasure = (point: THREE.Vector3) => {
      if (measurePoints.length === 2) clearMeasure()
      measurePoints.push(point.clone())
      const radius = Math.max(
        bounds.getBoundingSphere(new THREE.Sphere()).radius * 0.01,
        0.15
      )
      const marker = new THREE.Mesh(
        new THREE.SphereGeometry(radius, 16, 12),
        new THREE.MeshBasicMaterial({ color: 0xfbbf24 })
      )
      marker.position.copy(point)
      scene.add(marker)
      markers.push(marker)
      if (measurePoints.length === 1) setMessage("Pick second point")
      if (measurePoints.length === 2) {
        measureLine = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(measurePoints),
          new THREE.LineBasicMaterial({ color: 0xfbbf24 })
        )
        scene.add(measureLine)
        setMessage(
          `${measurePoints[0].distanceTo(measurePoints[1]).toFixed(3)} mm`
        )
      }
    }
    const pointerDown = (event: PointerEvent) => {
      if (!measureMode && !commentMode) return
      const rect = renderer.domElement.getBoundingClientRect()
      pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1
      )
      raycaster.setFromCamera(pointer, camera)
      const hit = raycaster.intersectObjects(
        meshes.filter((mesh) => mesh.visible),
        false
      )[0]
      if (!hit) return
      if (measureMode) {
        addMeasure(hit.point)
        return
      }
      const owner = hit.object as THREE.Mesh
      const localPoint = owner.worldToLocal(hit.point.clone())
      onPickComment({
        part: owner.name,
        position_mm: [localPoint.x, localPoint.y, localPoint.z],
        screen_position_px: [event.clientX - rect.left, event.clientY - rect.top],
        viewport_size_px: [rect.width, rect.height],
      })
      commentMode = false
      controls.enabled = true
      onCommentModeChange(false)
      setMessage("")
    }
    renderer.domElement.addEventListener("pointerdown", pointerDown)

    apiRef.current = {
      fit,
      setProjection: (next) => {
        const previous = camera
        camera = cameras[next]
        camera.position.copy(previous.position)
        camera.quaternion.copy(previous.quaternion)
        controls.object = camera
        updateOrtho()
        controls.update()
      },
      setRenderMode: (mode) => {
        meshes.forEach((mesh) => {
          const material = mesh.material as THREE.MeshStandardMaterial
              material.wireframe = false
          material.transparent = mode === "xray"
          material.opacity = mode === "xray" ? 0.28 : 1
          material.depthWrite = mode !== "xray"
          material.needsUpdate = true
        })
      },
      setGrid: (visible) => {
        gridHelper.visible = visible
      },
      setLabels: (visible) => {
        labelsVisible = visible
        annotationGroups.forEach((group) => {
          group.visible = visible
        })
        reviewGroups.forEach((group) => {
          group.visible = visible
        })
      },
      setCommentMode: (enabled) => {
        commentMode = enabled
        if (enabled) measureMode = false
        controls.enabled = !enabled
        setMessage(enabled ? "Pick a point for the comment" : "")
      },
      setMeasure: (enabled) => {
        measureMode = enabled
        if (enabled) commentMode = false
        controls.enabled = !enabled
        clearMeasure()
        setMessage(enabled ? "Pick first point" : "")
      },
      setPartVisible: (name, visible) => {
        const mesh = meshByName.get(name)
        if (mesh) mesh.visible = visible
      },
      setReviewComments: drawReviewComments,
    }
    const loader = new STLLoader()
    let disposed = false
    Promise.all(
      manifest.parts.map(async (part, index) => {
        const geometry = await loader.loadAsync(part.file)
        if (disposed) return
        geometry.computeVertexNormals()
        geometry.computeBoundingSphere()
        const mesh = new THREE.Mesh(
          geometry,
          new THREE.MeshStandardMaterial({
            color: part.color,
            roughness: 0.7,
            metalness: 0.03,
            side: THREE.DoubleSide,
          })
        )
        mesh.name = part.name
        mesh.visible = visibilityRef.current.get(part.name) !== false
        root.add(mesh)
        meshes[index] = mesh
        meshByName.set(part.name, mesh)
      })
    )
      .then(() => {
        if (disposed) return
        for (const annotation of manifest.annotations || []) {
          const point = new THREE.Vector3(...annotation.position_mm)
          const owner = annotation.part
            ? meshByName.get(annotation.part)
            : undefined
          const partSphere = owner?.geometry.boundingSphere
          const leaderLength = Math.max((partSphere?.radius || 20) * 0.52, 10)
          const partCenter = partSphere?.center || new THREE.Vector3()
          const offset = point.clone().sub(partCenter)
          if (offset.lengthSq() < 0.0001) offset.set(0, 0, 1)
          offset.normalize().multiplyScalar(leaderLength)

          const group = new THREE.Group()
          group.position.copy(point)
          const color = new THREE.Color(annotation.color || "#fbbf24")
          const leader = new THREE.Mesh(
            new THREE.CylinderGeometry(
              Math.max(leaderLength * 0.018, 0.12),
              Math.max(leaderLength * 0.018, 0.12),
              leaderLength,
              8
            ),
            new THREE.MeshBasicMaterial({
              color,
              depthTest: false,
              depthWrite: false,
            })
          )
          leader.renderOrder = 999
          leader.position.copy(offset).multiplyScalar(0.5)
          leader.quaternion.setFromUnitVectors(
            new THREE.Vector3(0, 1, 0),
            offset.clone().normalize()
          )
          const dot = new THREE.Mesh(
            new THREE.SphereGeometry(
              Math.max(leaderLength * 0.06, 0.18),
              12,
              8
            ),
            new THREE.MeshBasicMaterial({
              color,
              depthTest: false,
              depthWrite: false,
            })
          )
          dot.renderOrder = 999
          group.add(leader, dot)
          const label = makeLabelSprite(
            annotation.label,
            annotation.color || "#fbbf24",
            Math.max(leaderLength * 0.32, 2.8)
          )
          label.position.copy(offset)
          group.add(label)
          ;(owner || root).add(group)
          annotationGroups.push(group)
        }
        drawReviewComments(commentsRef.current)
        fit()
        setMessage("")
      })
      .catch((error: unknown) =>
        setMessage(
          error instanceof Error ? error.message : "Unable to load model"
        )
      )

    let frame = 0
    const animate = () => {
      controls.update()
      renderer.render(scene, camera)
      frame = requestAnimationFrame(animate)
    }
    const observer = new ResizeObserver(resize)
    observer.observe(host)
    resize()
    animate()
    return () => {
      disposed = true
      apiRef.current = null
      cancelAnimationFrame(frame)
      observer.disconnect()
      renderer.domElement.removeEventListener("pointerdown", pointerDown)
      controls.dispose()
      renderer.dispose()
      disposeObject(root)
    }
  }, [manifest, onCommentModeChange, onPickComment])

  const togglePart = (name: string) => {
    const visible = !partVisibility[name]
    visibilityRef.current.set(name, visible)
    setPartVisibility((current) => ({ ...current, [name]: visible }))
    apiRef.current?.setPartVisible(name, visible)
  }

  return (
    <div className="relative h-full min-h-0 overflow-hidden border bg-black/20 lg:min-h-[30rem]">
      <div ref={hostRef} className="absolute inset-0" />

      <div className="absolute top-2 left-2 hidden max-w-[calc(100%-1rem)] flex-wrap gap-1 rounded-md border bg-background/90 p-1 shadow-sm backdrop-blur-xl lg:flex">
        {(["solid", "xray"] as RenderMode[]).map((mode) => (
          <Button
            key={mode}
            size="sm"
            variant={renderMode === mode ? "secondary" : "ghost"}
            aria-pressed={renderMode === mode}
            onClick={() => {
              setRenderMode(mode)
              apiRef.current?.setRenderMode(mode)
            }}
          >
            {mode === "xray"
              ? "X-ray"
              : `${mode[0].toUpperCase()}${mode.slice(1)}`}
          </Button>
        ))}
        <div className="mx-0.5 w-px bg-border" />
        <Button
          size="sm"
          variant={labels ? "secondary" : "ghost"}
          aria-pressed={labels}
          onClick={() => {
            setLabels((current) => {
              apiRef.current?.setLabels(!current)
              return !current
            })
          }}
        >
          Labels
        </Button>
        <Button
          size="sm"
          variant={grid ? "secondary" : "ghost"}
          aria-pressed={grid}
          onClick={() => {
            setGrid((current) => {
              apiRef.current?.setGrid(!current)
              return !current
            })
          }}
        >
          Grid
        </Button>
        <Button
          size="sm"
          variant={measureMode ? "default" : "ghost"}
          aria-pressed={measureMode}
          onClick={() => {
            const next = !measureMode
            if (next) onCommentModeChange(false)
            onMeasureModeChange(next)
            apiRef.current?.setMeasure(next)
          }}
        >
          Measure
        </Button>
      </div>

      <div className="absolute top-2 left-2 flex gap-1 rounded-md border bg-background/90 p-1 shadow-sm backdrop-blur-xl lg:hidden">
        <details className="group relative">
          <summary className="flex h-8 cursor-pointer list-none items-center rounded-md px-3 text-xs font-medium group-open:bg-accent hover:bg-accent">
            More
          </summary>
          <div className="absolute top-10 left-0 w-56 space-y-3 rounded-md border bg-background/95 p-2 shadow-xl backdrop-blur-xl">
            <div className="grid grid-cols-2 gap-1">
              <Button
                size="sm"
                variant={renderMode === "xray" ? "secondary" : "ghost"}
                onClick={() => {
                  const next = renderMode === "xray" ? "solid" : "xray"
                  setRenderMode(next)
                  apiRef.current?.setRenderMode(next)
                }}
              >
                {renderMode === "xray" ? "Solid" : "X-ray"}
              </Button>
              <Button
                size="sm"
                variant={labels ? "secondary" : "ghost"}
                onClick={() => {
                  setLabels((current) => {
                    apiRef.current?.setLabels(!current)
                    return !current
                  })
                }}
              >
                Labels
              </Button>
              <Button
                size="sm"
                variant={grid ? "secondary" : "ghost"}
                onClick={() => {
                  setGrid((current) => {
                    apiRef.current?.setGrid(!current)
                    return !current
                  })
                }}
              >
                Grid
              </Button>
              <Button
                size="sm"
                variant={measureMode ? "default" : "ghost"}
                onClick={() => {
                  const next = !measureMode
                  if (next) onCommentModeChange(false)
                  onMeasureModeChange(next)
                  apiRef.current?.setMeasure(next)
                }}
              >
                Measure
              </Button>
            </div>
            <div className="flex flex-wrap gap-1 border-t pt-2">
              {manifest.parts.map((part) => (
                <Button
                  key={part.name}
                  size="sm"
                  variant={partVisibility[part.name] ? "secondary" : "ghost"}
                  aria-pressed={partVisibility[part.name]}
                  onClick={() => togglePart(part.name)}
                >
                  <span
                    className="size-2 rounded-full"
                    style={{ backgroundColor: part.color }}
                  />
                  {part.name}
                </Button>
              ))}
            </div>
          </div>
        </details>
      </div>

      <div className="absolute bottom-2 left-2 hidden max-w-[calc(100%-15rem)] flex-wrap gap-1 rounded-md border bg-background/90 p-1 shadow-sm backdrop-blur-xl lg:flex">
        {manifest.parts.map((part) => (
          <Button
            key={part.name}
            size="sm"
            variant={partVisibility[part.name] ? "secondary" : "ghost"}
            aria-pressed={partVisibility[part.name]}
            title={`${partVisibility[part.name] ? "Hide" : "Show"} ${part.name}`}
            className="max-w-44"
            onClick={() => togglePart(part.name)}
          >
            <span
              className="size-2 rounded-full"
              style={{ backgroundColor: part.color }}
            />
            <span className="truncate">{part.name}</span>
          </Button>
        ))}
      </div>

      {message && (
        <div className="absolute top-11 left-2 rounded bg-foreground px-2 py-1 text-[11px] text-background shadow">
          {message}
        </div>
      )}
    </div>
  )
}

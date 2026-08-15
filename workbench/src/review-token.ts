export function readReviewToken(): string {
  const fragment = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash
  const fragmentParams = new URLSearchParams(fragment)
  const fragmentToken = fragmentParams.get("token") || ""
  const currentUrl = new URL(window.location.href)
  const queryToken = currentUrl.searchParams.get("token") || ""

  if (queryToken) {
    currentUrl.searchParams.delete("token")
    if (!fragmentToken) fragmentParams.set("token", queryToken)
    currentUrl.hash = fragmentParams.toString()
    window.history.replaceState(
      window.history.state,
      "",
      `${currentUrl.pathname}${currentUrl.search}${currentUrl.hash}`
    )
  }

  return fragmentToken || queryToken
}

export function buildFocusedEventLink(
  baseLink: string | null | undefined,
  focusedEventId: string | null | undefined,
): string | null {
  if (!baseLink || !focusedEventId) return null;

  try {
    const url = new URL(baseLink);
    const hash = url.hash.startsWith("#") ? url.hash.slice(1) : url.hash;
    const [hashPath = "/events", hashQuery = ""] = hash.split("?");
    const params = new URLSearchParams(hashQuery);
    params.set("focusedEvent", focusedEventId);
    url.hash = `${hashPath}?${params.toString()}`;
    return url.toString();
  } catch {
    return null;
  }
}

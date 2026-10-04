// Poll only a read-only health endpoint; never replay a password or OTP request.
export async function waitForBackend(onWaiting: () => void, timeoutMs = 180000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch('/backend-api/health', {
        cache: 'no-store',
        signal: AbortSignal.timeout(Math.min(25000, deadline - Date.now())),
      });
      const data = await response.json().catch(() => null);
      if (response.ok && data?.status === 'ok') return;
    } catch {
      // A sleeping instance can initially return HTML, 502, or a timeout.
    }
    onWaiting();
    await new Promise(resolve => setTimeout(resolve, Math.min(5000, Math.max(0, deadline - Date.now()))));
  }
  throw new Error('The service is taking longer than expected to start. Please try again shortly.');
}

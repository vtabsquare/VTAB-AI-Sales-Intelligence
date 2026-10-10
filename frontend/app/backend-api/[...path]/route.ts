import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const BACKEND_BASE_URL = (
  process.env.API_BASE_URL ||
  process.env.BACKEND_API_BASE_URL ||
  "http://127.0.0.1:8001"
).replace(/\/$/, "");

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  try {
    const { path } = await context.params;
    const backendPath = path.join("/");
    const target = new URL(`${BACKEND_BASE_URL}/api/${backendPath}`);

    request.nextUrl.searchParams.forEach((value, key) => {
      target.searchParams.append(key, value);
    });

    const methodUpper = request.method.toUpperCase();
    const origin = request.headers.get('origin');
    if (!['GET','HEAD','OPTIONS'].includes(methodUpper) && origin && new URL(origin).host !== request.headers.get('host')) {
      return NextResponse.json({detail:'Cross-origin mutation rejected.'},{status:403});
    }
    const headers = new Headers();
    const contentType = request.headers.get("content-type");
    const accept = request.headers.get("accept");
    if (contentType) headers.set("content-type", contentType);
    if (accept) headers.set("accept", accept);
    const token =
      request.cookies.get("vtab_session")?.value;
    if (token) headers.set("authorization", `Bearer ${token}`);

    const method = request.method.toUpperCase();
    const hasBody = !["GET", "HEAD"].includes(method);
    const body = hasBody ? await request.arrayBuffer() : undefined;

    const upstream = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(backendPath === 'health' ? 25000 : backendPath.includes('discovery') || backendPath === 'sales-manager/run' || backendPath === 'sales-manager/sources/sync' || /^platform\/schedules\/[^/]+\/run$/.test(backendPath) ? 1800000 : 120000),
    });

    const responseBody = await upstream.arrayBuffer();
    const responseHeaders = new Headers();
    const upstreamContentType = upstream.headers.get("content-type");
    if (upstreamContentType) {
      responseHeaders.set("content-type", upstreamContentType);
    }

    const outgoing = new NextResponse(responseBody, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
    if (backendPath === "auth/verify" && upstream.ok) {
      try {
        const payload = JSON.parse(new TextDecoder().decode(responseBody));
        if (payload?.token) {
          const cookieOptions = {
            httpOnly: true,
            sameSite: "lax" as const,
            path: "/",
            secure: request.nextUrl.protocol === 'https:',
            maxAge: 480 * 60,
          };
          outgoing.cookies.set("vtab_session", payload.token, cookieOptions);
          outgoing.cookies.delete("vtab_auth_token");
        }
      } catch {}
    }
    if (upstream.status === 401 && !backendPath.startsWith('auth/')) outgoing.cookies.delete('vtab_session');
    if (backendPath === "auth/logout" && upstream.ok) {
      outgoing.cookies.delete("vtab_session");
      outgoing.cookies.delete("vtab_auth_token");
    }
    return outgoing;
  } catch (error) {
    return NextResponse.json(
      {
        detail: "The service is starting or temporarily unavailable. Please try again shortly.",

      },
      { status: 502 }
    );
  }
}

export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
  proxy as OPTIONS,
};

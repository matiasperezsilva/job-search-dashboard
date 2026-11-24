import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const response = await fetch("http://127.0.0.1:8000/health", {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    if (!response.ok) {
      return NextResponse.json({ status: "degraded", backend: false }, { status: 503 });
    }
    const commit = process.env.RENDER_GIT_COMMIT;
    const revision = commit && /^[a-f0-9]{40}$/.test(commit) ? commit.slice(0, 12) : undefined;
    return NextResponse.json({ status: "ok", frontend: true, backend: true, revision }, { status: 200 });
  } catch {
    return NextResponse.json({ status: "degraded", backend: false }, { status: 503 });
  }
}

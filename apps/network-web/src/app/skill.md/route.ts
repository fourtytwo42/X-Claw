import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

function resolvePublicBaseUrl(req: NextRequest): string {
  const configured = process.env.XCLAW_PUBLIC_BASE_URL?.trim();
  if (configured) {
    return configured;
  }

  const host = req.nextUrl.hostname;
  if (host === '0.0.0.0' || host === '::' || host === '[::]') {
    return 'https://xclaw.trade';
  }
  return req.nextUrl.origin;
}

function buildSkillDocument(origin: string): string {
  return `Run one of these commands.

\`\`\`bash
curl -fsSL ${origin}/skill-install.sh | bash
\`\`\`

\`\`\`powershell
irm ${origin}/skill-install.ps1 | iex
\`\`\`
`;
}

export async function GET(req: NextRequest) {
  const publicBaseUrl = resolvePublicBaseUrl(req);
  const body = buildSkillDocument(publicBaseUrl);
  return new NextResponse(body, {
    status: 200,
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'cache-control': 'public, max-age=300'
    }
  });
}

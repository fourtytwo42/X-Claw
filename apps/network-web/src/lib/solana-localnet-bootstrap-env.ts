import fs from 'node:fs';
import path from 'node:path';

const DEFAULT_BOOTSTRAP_ENV_PATH = path.resolve(process.cwd(), 'infrastructure', 'seed-data', 'solana-localnet-faucet.env');

let cachedPath = '';
let cachedMtime = 0;
let cachedValues: Record<string, string> = {};

function readEnvFile(envPath: string): Record<string, string> {
  try {
    const stat = fs.statSync(envPath);
    if (envPath === cachedPath && stat.mtimeMs === cachedMtime) {
      return cachedValues;
    }
    const text = fs.readFileSync(envPath, 'utf8');
    const next: Record<string, string> = {};
    for (const rawLine of text.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith('#')) continue;
      const eq = line.indexOf('=');
      if (eq <= 0) continue;
      const key = line.slice(0, eq).trim();
      const value = line.slice(eq + 1).trim();
      if (key) {
        next[key] = value;
      }
    }
    cachedPath = envPath;
    cachedMtime = stat.mtimeMs;
    cachedValues = next;
    return next;
  } catch {
    return {};
  }
}

export function resolveSolanaLocalnetBootstrapEnv(prefix: string, chainKey: string): string {
  if (String(chainKey || '').trim().toLowerCase() !== 'solana_localnet') {
    return '';
  }
  const envPath = (process.env.XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE || DEFAULT_BOOTSTRAP_ENV_PATH).trim();
  if (!envPath) {
    return '';
  }
  const suffix = chainKey.replace(/[^a-zA-Z0-9]/g, '_').toUpperCase();
  const values = readEnvFile(envPath);
  return String(values[`${prefix}_${suffix}`] || '').trim();
}

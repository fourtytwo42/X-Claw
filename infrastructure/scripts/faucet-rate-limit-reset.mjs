import { createClient } from 'redis';

const redisUrl = process.env.REDIS_URL;
if (!redisUrl) {
  console.error(
    JSON.stringify({
      ok: false,
      code: 'missing_env',
      message: 'REDIS_URL is required.',
      actionHint: 'Export REDIS_URL (for example via `set -a; source .env.local; set +a`) and retry.'
    })
  );
  process.exit(1);
}

const PREFIX = 'xclaw:ratelimit:v1:agent_faucet_daily:';
const MATCH = `${PREFIX}*`;

const client = createClient({ url: redisUrl });
client.on('error', () => {
  // surfaced by awaited calls
});

let deleted = 0;
let scanned = 0;
const deletedSamples = [];

try {
  await client.connect();
  for await (const key of client.scanIterator({ MATCH, COUNT: 500 })) {
    scanned += 1;
    await client.del(key);
    deleted += 1;
    if (deletedSamples.length < 20) {
      deletedSamples.push(key);
    }
  }
  console.log(
    JSON.stringify({
      ok: true,
      code: 'ok',
      message: 'Faucet daily rate-limit keys reset.',
      pattern: MATCH,
      scanned,
      deleted,
      deletedSamples
    })
  );
} catch (error) {
  const msg = error instanceof Error ? error.message : String(error);
  console.error(
    JSON.stringify({
      ok: false,
      code: 'redis_operation_failed',
      message: msg,
      actionHint: 'Verify REDIS_URL connectivity and retry.'
    })
  );
  process.exit(1);
} finally {
  try {
    await client.quit();
  } catch {
    // ignore
  }
}

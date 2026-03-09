import bs58 from 'bs58';

import {
  Connection,
  Keypair,
  LAMPORTS_PER_SOL,
  PublicKey,
  SendOptions,
  SystemProgram,
  Transaction,
} from '@solana/web3.js';
import {
  getOrCreateAssociatedTokenAccount,
  mintTo,
  transfer as splTransfer,
} from '@solana/spl-token';

export type SolanaFaucetAsset = 'native' | 'wrapped' | 'stable';

const DEFAULT_CONFIRM_TIMEOUT_MS = 30_000;

export function isLikelySolanaAddress(value: string): boolean {
  const text = String(value || '').trim();
  return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(text);
}

export function parseSolanaSecret(secret: string): Uint8Array {
  const raw = String(secret || '').trim();
  if (!raw) {
    throw new Error('missing_signer_secret');
  }
  if (raw.startsWith('[') && raw.endsWith(']')) {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length !== 64) {
      throw new Error('invalid_signer_secret_json');
    }
    return Uint8Array.from(parsed);
  }
  const decoded = bs58.decode(raw);
  if (decoded.length !== 64) {
    throw new Error('invalid_signer_secret_base58');
  }
  return decoded;
}

async function confirmSignature(
  connection: Connection,
  signature: string,
  confirmOptions?: SendOptions
): Promise<void> {
  const strategy = await connection.getLatestBlockhash(confirmOptions?.preflightCommitment || 'confirmed');
  const started = Date.now();
  for (;;) {
    const status = await connection.getSignatureStatuses([signature], {
      searchTransactionHistory: true,
    });
    const entry = status.value[0];
    if (entry?.confirmationStatus === 'confirmed' || entry?.confirmationStatus === 'finalized') {
      return;
    }
    if (entry?.err) {
      throw new Error(`solana_signature_failed:${JSON.stringify(entry.err)}`);
    }
    if (Date.now() - started > DEFAULT_CONFIRM_TIMEOUT_MS) {
      throw new Error('solana_signature_confirmation_timeout');
    }
    if (strategy.lastValidBlockHeight > 0) {
      const currentHeight = await connection.getBlockHeight(confirmOptions?.preflightCommitment || 'confirmed');
      if (currentHeight > strategy.lastValidBlockHeight) {
        throw new Error('solana_signature_blockhash_expired');
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

export async function sendNativeSol(
  connection: Connection,
  signer: Keypair,
  recipient: PublicKey,
  lamports: bigint
): Promise<string> {
  const latest = await connection.getLatestBlockhash('confirmed');
  const tx = new Transaction({
    feePayer: signer.publicKey,
    recentBlockhash: latest.blockhash,
  }).add(
    SystemProgram.transfer({
      fromPubkey: signer.publicKey,
      toPubkey: recipient,
      lamports: Number(lamports),
    })
  );
  tx.sign(signer);
  const options = {
    skipPreflight: false,
    preflightCommitment: 'confirmed',
    maxRetries: 3,
  } satisfies SendOptions;
  const signature = await connection.sendRawTransaction(tx.serialize(), options);
  await confirmSignature(connection, signature, options);
  return signature;
}

export async function airdropNativeSol(connection: Connection, recipient: PublicKey, lamports: bigint): Promise<string> {
  const signature = await connection.requestAirdrop(recipient, Number(lamports));
  await confirmSignature(connection, signature, { preflightCommitment: 'confirmed', maxRetries: 3 });
  return signature;
}

export async function dripSplToken(
  connection: Connection,
  signer: Keypair,
  recipient: PublicKey,
  mint: PublicKey,
  amountUnits: bigint
): Promise<string> {
  const recipientAta = await getOrCreateAssociatedTokenAccount(
    connection,
    signer,
    mint,
    recipient
  );
  try {
    const signature = await mintTo(
      connection,
      signer,
      mint,
      recipientAta.address,
      signer.publicKey,
      amountUnits
    );
    return signature;
  } catch {
    const faucetAta = await getOrCreateAssociatedTokenAccount(
      connection,
      signer,
      mint,
      signer.publicKey
    );
    const signature = await splTransfer(
      connection,
      signer,
      faucetAta.address,
      recipientAta.address,
      signer.publicKey,
      amountUnits
    );
    return signature;
  }
}

export function parsePositiveUnits(value: string, field: string): bigint {
  const parsed = BigInt(String(value || '').trim());
  if (parsed <= BigInt(0)) {
    throw new Error(`${field}_non_positive`);
  }
  return parsed;
}

export function defaultNativeLamports(): bigint {
  return BigInt(LAMPORTS_PER_SOL);
}

import bs58 from 'bs58';

import {
  Connection,
  Keypair,
  LAMPORTS_PER_SOL,
  PublicKey,
  SystemProgram,
  Transaction,
} from '@solana/web3.js';
import {
  getOrCreateAssociatedTokenAccount,
  mintTo,
  transfer as splTransfer,
} from '@solana/spl-token';

export type SolanaFaucetAsset = 'native' | 'wrapped' | 'stable';

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

export async function sendNativeSol(
  connection: Connection,
  signer: Keypair,
  recipient: PublicKey,
  lamports: bigint
): Promise<string> {
  const tx = new Transaction().add(
    SystemProgram.transfer({
      fromPubkey: signer.publicKey,
      toPubkey: recipient,
      lamports: Number(lamports),
    })
  );
  const signature = await connection.sendTransaction(tx, [signer], {
    skipPreflight: false,
    preflightCommitment: 'confirmed',
    maxRetries: 3,
  });
  await connection.confirmTransaction(signature, 'confirmed');
  return signature;
}

export async function airdropNativeSol(connection: Connection, recipient: PublicKey, lamports: bigint): Promise<string> {
  const signature = await connection.requestAirdrop(recipient, Number(lamports));
  await connection.confirmTransaction(signature, 'confirmed');
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
    await connection.confirmTransaction(signature, 'confirmed');
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
    await connection.confirmTransaction(signature, 'confirmed');
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

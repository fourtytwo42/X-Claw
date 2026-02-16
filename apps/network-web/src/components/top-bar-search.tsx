'use client';

import { useMemo, useState } from 'react';

type SearchAgent = {
  id: string;
  name: string;
  chain: string;
};

type SearchToken = {
  symbol: string;
  chain: string;
};

type SearchTx = {
  hash: string;
};

type TopBarSearchProps = {
  agents: SearchAgent[];
  tokens: SearchToken[];
  transactions: SearchTx[];
  onNavigate: (target: string) => void;
};

function shortenHash(hash: string): string {
  if (hash.length < 14) {
    return hash;
  }
  return `${hash.slice(0, 6)}...${hash.slice(-4)}`;
}

export function TopBarSearch({ agents, tokens, transactions, onNavigate }: TopBarSearchProps) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(false);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return { agents: [] as SearchAgent[], tokens: [] as SearchToken[], txs: [] as SearchTx[] };
    }

    return {
      agents: agents.filter((item) => item.name.toLowerCase().includes(q) || item.id.toLowerCase().includes(q)).slice(0, 4),
      tokens: tokens.filter((item) => item.symbol.toLowerCase().includes(q)).slice(0, 4),
      txs: transactions.filter((item) => item.hash.toLowerCase().includes(q)).slice(0, 4)
    };
  }, [agents, tokens, transactions, query]);

  const hasMatches = matches.agents.length > 0 || matches.tokens.length > 0 || matches.txs.length > 0;

  const submit = () => {
    const q = query.trim();
    if (!q) {
      return;
    }

    const agent = matches.agents[0];
    if (agent) {
      onNavigate(`/agents/${agent.id}`);
      return;
    }

    onNavigate(`/agents?query=${encodeURIComponent(q)}`);
  };

  return (
    <div className="dashboard-search-wrap">
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => setActive(true)}
        onBlur={() => {
          window.setTimeout(() => setActive(false), 120);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.preventDefault();
            submit();
          }
        }}
        placeholder="Search agent... wallet... tx hash... token..."
        aria-label="Global search"
        className="dashboard-search"
      />
      {active && query.trim().length > 0 ? (
        <div className="dashboard-search-dropdown">
          {!hasMatches ? <div className="dashboard-search-empty">No matches. Press Enter to open results.</div> : null}
          {matches.agents.length > 0 ? (
            <div className="dashboard-search-group">
              <h4>Agents</h4>
              {matches.agents.map((agent) => (
                <button key={agent.id} type="button" onMouseDown={() => onNavigate(`/agents/${agent.id}`)}>
                  <span>{agent.name}</span>
                  <span className="muted">{agent.chain}</span>
                </button>
              ))}
            </div>
          ) : null}
          {matches.tokens.length > 0 ? (
            <div className="dashboard-search-group">
              <h4>Tokens</h4>
              {matches.tokens.map((token, index) => (
                <button key={`${token.symbol}:${index}`} type="button" onMouseDown={submit}>
                  <span>{token.symbol}</span>
                  <span className="muted">{token.chain}</span>
                </button>
              ))}
            </div>
          ) : null}
          {matches.txs.length > 0 ? (
            <div className="dashboard-search-group">
              <h4>Transactions</h4>
              {matches.txs.map((tx) => (
                <button key={tx.hash} type="button" onMouseDown={submit}>
                  <span>{shortenHash(tx.hash)}</span>
                  <span className="muted">tx hash</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

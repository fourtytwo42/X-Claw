import { Suspense } from 'react';

import ExplorePage from '@/app/explore/page';

export default function AgentsAliasPage() {
  return (
    <Suspense fallback={null}>
      <ExplorePage />
    </Suspense>
  );
}

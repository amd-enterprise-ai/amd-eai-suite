// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { StoryContext } from './story-context';
import { MDXProvider } from '@mdx-js/react';
import { components } from './components';

// Use dynamic path to avoid circular alias issues
// @ts-expect-error - This path is resolved by Vite alias to the actual @ladle/react package
export * from '@ladle/react-original';

// @ts-expect-error - Same as above
import { Story as OriginalStory } from '@ladle/react-original';

// Re-export the context
export { StoryContext };

// Custom Story wrapper that provides context and MDX components (overrides the re-exported Story)
type StoryProps = React.ComponentProps<typeof OriginalStory>;
export const Story = (props: StoryProps) => (
  <StoryContext.Provider value={true}>
    <MDXProvider components={components}>
      <OriginalStory {...props} />
    </MDXProvider>
  </StoryContext.Provider>
);

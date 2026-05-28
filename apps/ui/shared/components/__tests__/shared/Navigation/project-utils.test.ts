// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, expect, it } from 'vitest';

import {
  buildProjectHref,
  stripProjectPrefix,
} from '@/src/Navigation/project-utils';

describe('project-utils', () => {
  describe('buildProjectHref', () => {
    it('returns href unchanged when no project prefix', () => {
      expect(buildProjectHref('/models')).toBe('/models');
      expect(buildProjectHref('/models', undefined)).toBe('/models');
    });

    it('prefixes href with project', () => {
      expect(buildProjectHref('/models', 'my-project')).toBe(
        '/my-project/models',
      );
    });

    it('normalizes href without leading slash', () => {
      expect(buildProjectHref('models', 'my-project')).toBe(
        '/my-project/models',
      );
    });

    it('handles nested paths', () => {
      expect(buildProjectHref('/aims/123/details', 'my-project')).toBe(
        '/my-project/aims/123/details',
      );
    });

    it('handles root path', () => {
      expect(buildProjectHref('/', 'my-project')).toBe('/my-project/');
    });
  });

  describe('stripProjectPrefix', () => {
    describe('without locale', () => {
      it('returns pathname unchanged when no project prefix', () => {
        expect(stripProjectPrefix('/models')).toBe('/models');
        expect(stripProjectPrefix('/models', undefined)).toBe('/models');
      });

      it('returns null for null pathname', () => {
        expect(stripProjectPrefix(null, 'my-project')).toBeNull();
      });

      it('strips project prefix from pathname', () => {
        expect(stripProjectPrefix('/my-project/models', 'my-project')).toBe(
          '/models',
        );
      });

      it('returns root for project-only path', () => {
        expect(stripProjectPrefix('/my-project', 'my-project')).toBe('/');
      });

      it('returns root for project path with trailing slash', () => {
        expect(stripProjectPrefix('/my-project/', 'my-project')).toBe('/');
      });

      it('handles nested paths', () => {
        expect(
          stripProjectPrefix('/my-project/aims/123/details', 'my-project'),
        ).toBe('/aims/123/details');
      });

      it('returns pathname unchanged when project does not match', () => {
        expect(stripProjectPrefix('/other-project/models', 'my-project')).toBe(
          '/other-project/models',
        );
      });
    });

    describe('with locale prefix', () => {
      it('strips locale and project prefix for non-default locale', () => {
        expect(
          stripProjectPrefix('/de/my-project/models', 'my-project', 'de', 'en'),
        ).toBe('/models');
      });

      it('returns root for locale + project only path', () => {
        expect(
          stripProjectPrefix('/de/my-project', 'my-project', 'de', 'en'),
        ).toBe('/');
      });

      it('returns root for locale + project path with trailing slash', () => {
        expect(
          stripProjectPrefix('/de/my-project/', 'my-project', 'de', 'en'),
        ).toBe('/');
      });

      it('handles locale-only path', () => {
        expect(stripProjectPrefix('/de', 'my-project', 'de', 'en')).toBe('/');
      });

      it('does not strip locale when it matches default locale', () => {
        expect(
          stripProjectPrefix('/my-project/models', 'my-project', 'en', 'en'),
        ).toBe('/models');
      });

      it('handles nested paths with locale', () => {
        expect(
          stripProjectPrefix(
            '/de/my-project/aims/123/details',
            'my-project',
            'de',
            'en',
          ),
        ).toBe('/aims/123/details');
      });

      it('handles path without project but with locale', () => {
        expect(stripProjectPrefix('/de/models', 'my-project', 'de', 'en')).toBe(
          '/models',
        );
      });
    });
  });
});

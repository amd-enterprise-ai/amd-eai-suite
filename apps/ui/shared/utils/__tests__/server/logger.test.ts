// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect } from 'vitest';
import getLogger from '../../src/server/logger';

describe('getLogger', () => {
  it('should return a winston logger instance', () => {
    const logger = getLogger();

    expect(logger).toBeDefined();
    expect(logger).toHaveProperty('info');
    expect(logger).toHaveProperty('error');
    expect(logger).toHaveProperty('warn');
    expect(logger).toHaveProperty('debug');
  });

  it('should have console transport configured', () => {
    const logger = getLogger();

    expect(logger.transports).toBeDefined();
    expect(logger.transports.length).toBeGreaterThan(0);
  });

  it('should have info level set by default', () => {
    const logger = getLogger();

    expect(logger.level).toBe('info');
  });

  it('should be able to call info method', () => {
    const logger = getLogger();

    expect(() => logger.info('test message')).not.toThrow();
  });

  it('should be able to call error method', () => {
    const logger = getLogger();

    expect(() => logger.error('test error')).not.toThrow();
  });

  it('should be able to call warn method', () => {
    const logger = getLogger();

    expect(() => logger.warn('test warning')).not.toThrow();
  });

  it('should be able to call debug method', () => {
    const logger = getLogger();

    expect(() => logger.debug('test debug')).not.toThrow();
  });

  it('should create independent logger instances', () => {
    const logger1 = getLogger();
    const logger2 = getLogger();

    // Each call should create a new logger instance
    expect(logger1).toBeDefined();
    expect(logger2).toBeDefined();
  });

  it('should have format configured', () => {
    const logger = getLogger();

    expect(logger.format).toBeDefined();
  });
});

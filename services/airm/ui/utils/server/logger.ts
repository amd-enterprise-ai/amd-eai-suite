// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import winston from 'winston';

const getLogger = () =>
  winston.createLogger({
    level: 'info',
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
      winston.format.printf(({ level, message, timestamp, ...metadata }) => {
        const metaString = Object.keys(metadata).length
          ? `\n${JSON.stringify(metadata, null, 2)}`
          : '';
        return `${timestamp} ${level}: ${message}${metaString}`;
      }),
    ),
    transports: [
      // new winston.transports.File({ filename: 'error.log', level: 'error' }),
      // new winston.transports.File({ filename: 'combined.log' }),
      new winston.transports.Console(),
    ],
  });

export default getLogger;

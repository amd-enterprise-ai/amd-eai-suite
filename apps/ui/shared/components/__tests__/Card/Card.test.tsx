// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import {
  Card,
  CardBody,
  CardHeader,
  CardFooter,
} from '@amdenterpriseai/components';

describe('Card adapter', () => {
  describe('flat imports', () => {
    it('renders Card with CardBody', () => {
      render(
        <Card data-testid="card">
          <CardBody data-testid="card-body">Content</CardBody>
        </Card>,
      );

      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(screen.getByTestId('card-body')).toHaveTextContent('Content');
    });

    it('renders Card with CardHeader and CardFooter', () => {
      render(
        <Card data-testid="card">
          <CardHeader data-testid="card-header">Header</CardHeader>
          <CardFooter data-testid="card-footer">Footer</CardFooter>
        </Card>,
      );

      expect(screen.getByTestId('card-header')).toHaveTextContent('Header');
      expect(screen.getByTestId('card-footer')).toHaveTextContent('Footer');
    });
  });

  describe('compound imports', () => {
    it('exposes Body as a static property', () => {
      expect(Card.Body).toBe(CardBody);
    });

    it('exposes Header as a static property', () => {
      expect(Card.Header).toBe(CardHeader);
    });

    it('exposes Footer as a static property', () => {
      expect(Card.Footer).toBe(CardFooter);
    });

    it('renders using compound syntax', () => {
      render(
        <Card data-testid="card">
          <Card.Header data-testid="card-header">Header</Card.Header>
          <Card.Body data-testid="card-body">Body</Card.Body>
          <Card.Footer data-testid="card-footer">Footer</Card.Footer>
        </Card>,
      );

      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(screen.getByTestId('card-header')).toHaveTextContent('Header');
      expect(screen.getByTestId('card-body')).toHaveTextContent('Body');
      expect(screen.getByTestId('card-footer')).toHaveTextContent('Footer');
    });
  });
});

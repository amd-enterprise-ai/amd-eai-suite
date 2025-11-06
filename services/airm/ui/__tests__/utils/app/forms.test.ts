// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { parseFormData } from '@/utils/app/forms';

import { describe, expect, it } from 'vitest';

describe('parseFormData', () => {
  it('should parse single input form data correctly', () => {
    const form = document.createElement('form');
    const input = document.createElement('input');
    input.name = 'username';
    input.value = 'testuser';
    form.appendChild(input);

    const result = parseFormData(form);
    expect(result).toEqual({ username: 'testuser' });
  });

  it('should parse multiple input form data correctly', () => {
    const form = document.createElement('form');
    const input1 = document.createElement('input');
    input1.name = 'username';
    input1.value = 'testuser';
    const input2 = document.createElement('input');
    input2.name = 'email';
    input2.value = 'testuser@example.com';
    form.appendChild(input1);
    form.appendChild(input2);

    const result = parseFormData(form);
    expect(result).toEqual({
      username: 'testuser',
      email: 'testuser@example.com',
    });
  });

  it('should parse multi-select form data correctly', () => {
    const form = document.createElement('form');
    const select = document.createElement('select');
    select.name = 'colors';
    select.multiple = true;
    const option1 = document.createElement('option');
    option1.value = 'red';
    option1.selected = true;
    const option2 = document.createElement('option');
    option2.value = 'blue';
    option2.selected = true;
    select.appendChild(option1);
    select.appendChild(option2);
    form.appendChild(select);

    const result = parseFormData(form);
    expect(result).toEqual({ colors: ['red', 'blue'] });
  });

  it('should handle multiple elements with the same name correctly', () => {
    const form = document.createElement('form');
    const input1 = document.createElement('input');
    input1.name = 'hobbies';
    input1.value = 'reading';
    const input2 = document.createElement('input');
    input2.name = 'hobbies';
    input2.value = 'coding';
    form.appendChild(input1);
    form.appendChild(input2);

    const result = parseFormData(form);
    expect(result).toEqual({ hobbies: ['reading', 'coding'] });
  });
});

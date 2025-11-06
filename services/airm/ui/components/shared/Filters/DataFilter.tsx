// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem, cn } from '@heroui/react';
import { createRef, useCallback, useMemo, useState } from 'react';
import { useRef } from 'react';

import { useTranslation } from 'next-i18next';

import { getDefaultFilterValues } from '@/utils/app/data-table';

import { FilterComponentType } from '@/types/enums/filters';
import { FilterFieldMapping, FilterValueMap } from '@/types/filters';

import SearchInput from './SearchInput';
import ClearFiltersButton from './ClearFiltersButton';
import FilterDropdown from './FilterDropdown';

import { isEqual } from 'lodash';

interface Props {
  filters: FilterFieldMapping;
  onFilterChange: (filters: FilterValueMap) => void;
  canClear?: boolean;
}

export const DataFilter = ({
  filters,
  onFilterChange,
  canClear = true,
}: Props) => {
  const { t } = useTranslation('common');

  const [filterValues, setFilterValues] = useState<Partial<FilterValueMap>>(
    getDefaultFilterValues(filters),
  );

  // Store debounce inputs per filter key
  const debounceInputRef = useRef<
    Record<string, React.RefObject<{ clear: () => void } | null>>
  >({});

  // Store FilterDropdown refs per filter key
  const filterDropdownRef = useRef<
    Record<string, React.RefObject<{ clear: () => void } | null>>
  >({});

  // Memoize default values to avoid recalculating on every render
  const defaultValues = useMemo(
    () => getDefaultFilterValues(filters),
    [filters],
  );

  const clearFilters = useCallback(() => {
    // Reset FilterDropdown components directly via refs
    Object.keys(filters).forEach((key) => {
      const filter = filters[key as keyof typeof filters];

      if (filter.type === FilterComponentType.DROPDOWN) {
        const dropdownRef = filterDropdownRef.current[key]?.current;
        if (dropdownRef) {
          dropdownRef.clear();
        }
      }

      if (filter.type === FilterComponentType.TEXT) {
        const input = debounceInputRef.current[key]?.current;
        if (input) {
          input.clear();
        }
      }
    });

    setFilterValues(defaultValues);
    onFilterChange(defaultValues as FilterValueMap);
  }, [filters, onFilterChange, defaultValues]);

  const isClearButtonDisabled = useMemo(() => {
    return isEqual(filterValues, defaultValues);
  }, [filterValues, defaultValues]);

  return (
    <>
      {Object.keys(filters).map((key) => {
        const filter = filters[key as keyof typeof filters];

        if (filter.type === FilterComponentType.TEXT) {
          return (
            <SearchInput
              key={`filter-input-${String(key)}`}
              className={cn(
                'w-[calc(100%-3.3rem)] md:w-[calc(100%-3.4rem)] lg:max-w-48',
                filter.className,
              )}
              aria-label={filter.label}
              placeholder={filter.placeholder}
              onValueChange={(value) => {
                // Keep state for all filter values
                setFilterValues((prev) => {
                  const trimmed = value?.trim();
                  if (!trimmed) {
                    if (prev[key] === undefined) return prev;
                    const { [key]: _, ...rest } = prev;
                    onFilterChange(rest as FilterValueMap);
                    return rest;
                  }
                  const newValues = { ...prev, [key]: [trimmed] };
                  onFilterChange(newValues as FilterValueMap);
                  return newValues;
                });
              }}
              canClear={false}
              ref={(() => {
                if (!debounceInputRef.current[key]) {
                  debounceInputRef.current[key] = createRef<{
                    clear: () => void;
                  }>();
                }
                return debounceInputRef.current[key];
              })()}
            />
          );
        }

        if (filter.type === FilterComponentType.SELECT) {
          return (
            <Select
              key={`select-filter-${filter.name}-${String(key)}`}
              selectionMode={
                filter.allowMultipleSelection ? 'multiple' : undefined
              }
              aria-label={filter.label}
              className={cn(
                'w-full md:w-[calc(50%-0.5rem)] lg:w-48',
                filter.className,
              )}
              startContent={filter.icon}
              placeholder={filter.placeholder}
              defaultSelectedKeys={filter.defaultSelectedValues?.map(String)}
              selectedKeys={
                Array.isArray(filterValues[key])
                  ? (filterValues[key] as (string | number | boolean)[]).map(
                      String,
                    )
                  : []
              }
              onSelectionChange={(values) => {
                setFilterValues((prev) => {
                  const newValues = {
                    ...prev,
                    [key]: Array.from(values).map((item) => String(item)),
                  };
                  onFilterChange(newValues as FilterValueMap);
                  return newValues;
                });
              }}
            >
              {filter?.fields
                ? filter.fields.map((field) => (
                    <SelectItem key={String(field.key)} {...field.props}>
                      {field.label}
                    </SelectItem>
                  ))
                : null}
            </Select>
          );
        }

        if (filter.type === FilterComponentType.DROPDOWN) {
          return (
            <FilterDropdown
              key={`dropdown-filter-${String(key)}`}
              ref={(() => {
                if (!filterDropdownRef.current[key]) {
                  filterDropdownRef.current[key] = createRef<{
                    clear: () => void;
                  }>();
                }
                return filterDropdownRef.current[key];
              })()}
              icon={filter.icon}
              className={cn(
                'w-full md:w-[calc(50%-0.5rem)] lg:w-48',
                filter.className,
              )}
              items={(filter.fields ?? []).map((field) => {
                return {
                  ...field.props,
                  key: String(field.key),
                  label: t(field.label),
                  description: String(field.label),
                };
              })}
              defaultSelectedKeys={
                filter.defaultSelectedValues
                  ? filter.defaultSelectedValues.map((value) => String(value))
                  : undefined
              }
              showDescription={filter.showFieldDescription ? true : false}
              selectedKeys={
                Array.isArray(filterValues[key])
                  ? (filterValues[key] as (string | number | boolean)[]).map(
                      String,
                    )
                  : undefined
              }
              onSelectionChange={(selected) => {
                return setFilterValues((prev) => {
                  const newValues = {
                    ...prev,
                    [key]: selected
                      ? Array.from(selected).map((item) => String(item))
                      : [],
                  };
                  onFilterChange(newValues as FilterValueMap);
                  return newValues;
                });
              }}
              label={t(filter.label)}
            />
          );
        }

        throw new Error(`Unsupported filter type: ${filter.type}`);
      })}
      {canClear && Object.keys(filters).length > 0 && (
        <ClearFiltersButton
          isDisabled={isClearButtonDisabled}
          onPress={clearFilters}
        />
      )}
    </>
  );
};

export default DataFilter;

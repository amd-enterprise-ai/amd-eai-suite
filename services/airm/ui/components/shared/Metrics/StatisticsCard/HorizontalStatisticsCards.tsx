// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { StatisticsCard, StatisticsCardProps } from './StatisticsCard';

interface Props {
  cards: StatisticsCardProps[];
  isLoading?: boolean;
}

export const HorizontalStatisticsCards: React.FC<Props> = ({
  cards,
  isLoading = false,
}) => (
  <div className="max-w-[1250px] gap-4 grid grid-rows-1 sm:flex-cols-1 md:grid-cols-2 xl:grid-cols-4">
    {cards.map((card) => {
      return (
        <StatisticsCard
          key={card.title}
          title={card.title}
          tooltip={card.tooltip}
          statistic={card.statistic}
          upperLimit={card.upperLimit}
          isLoading={isLoading}
        />
      );
    })}
  </div>
);
